import asyncio
import json
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from pydantic import BaseModel, Field

from commons.constants import OPENAI_API_KEY, OPENAI_EMBEDDINGS_MODEL, OPENAI_HOST
from t6_grounding.user_service_client import UserServiceClient

# The proxy uses DIAL-style deployment routing (same convention as OPENAI_CHAT_COMPLETIONS_ENDPOINT).
# The SDK appends "/chat/completions" and "/embeddings" itself, so they must not be part of base_url.
_LUNA_MODEL = "gpt-5.6-luna-2026-07-09"
_LUNA_BASE_URL = f"{OPENAI_HOST}/openai/deployments/{_LUNA_MODEL}"
_EMBEDDINGS_BASE_URL = f"{OPENAI_HOST}/openai/deployments/text-embedding-3-small-1"

SYSTEM_PROMPT = """You are performing Named Entity Extraction (NER) to group users by hobby.

You will be given a list of candidate users (each with a USER ID and their "about_me" text) and a search question.
- Identify the hobbies mentioned in the "about_me" texts that are relevant to the search question.
- For each relevant hobby, list the USER IDs of the users whose "about_me" text mentions that hobby.
- Return ONLY user IDs - never repeat or include any personal information about the users.
- If a user does not clearly match any relevant hobby, omit them.
- If no users match, return an empty mapping.
"""

USER_PROMPT = """##CANDIDATE USERS:
{context}


##SEARCH QUESTION:
{query}"""


class HobbyGroup(BaseModel):
    hobby: str = Field(description="Hobby name")
    user_ids: list[int] = Field(description="IDs of users whose about_me mentions this hobby")


class HobbyGroups(BaseModel):
    hobbies: list[HobbyGroup] = Field(
        description="List of hobbies with the IDs of matching users",
    )


def format_user_document(user: dict[str, Any]) -> Document:
    """Build a Document that embeds only `about_me`; the user id travels as metadata/id."""
    return Document(page_content=user.get("about_me", ""), metadata={"user_id": user["id"]})


class HobbySearchWizard:
    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self._llm_client = OpenAI(api_key=OPENAI_API_KEY, base_url=_LUNA_BASE_URL)
        self._user_client = UserServiceClient()
        self.vectorstore: Optional[Chroma] = None

    async def __aenter__(self):
        print("🔎 Loading all users...")
        users = self._user_client.get_all_users()

        self.vectorstore = Chroma(embedding_function=self.embeddings, collection_name="users_hobbies")

        print(f"↗️ Creating embeddings and vectorstore for {len(users)} users...")
        await self._add_users_batched(users, batch_size=100)

        print("✅ Vectorstore is ready.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _add_users_batched(self, users: list[dict[str, Any]], batch_size: int = 100):
        batches = [users[i:i + batch_size] for i in range(0, len(users), batch_size)]

        coroutines = [self._add_batch(batch) for batch in batches]
        await asyncio.gather(*coroutines)

    async def _add_batch(self, batch: list[dict[str, Any]]):
        documents = [format_user_document(user) for user in batch]
        ids = [str(user["id"]) for user in batch]
        await self.vectorstore.aadd_documents(documents, ids=ids)

    async def _sync_vectorstore(self):
        """Refresh the vectorstore to match the current state of the User Service."""
        users = self._user_client.get_all_users()
        users_by_id = {str(user["id"]): user for user in users}

        current_ids = set(users_by_id.keys())
        existing_ids = set(self.vectorstore.get()["ids"])

        deleted_ids = existing_ids - current_ids
        new_ids = current_ids - existing_ids

        if deleted_ids:
            print(f"🗑️ Removing {len(deleted_ids)} deleted user(s) from vectorstore...")
            self.vectorstore.delete(ids=list(deleted_ids))

        if new_ids:
            print(f"➕ Adding {len(new_ids)} new user(s) to vectorstore...")
            new_users = [users_by_id[user_id] for user_id in new_ids]
            documents = [format_user_document(user) for user in new_users]
            self.vectorstore.add_documents(documents, ids=list(new_ids))

    async def retrieve_context(self, query: str, k: int = 10, score: float = 0.1) -> list[dict[str, Any]]:
        print("Retrieving context...")
        await self._sync_vectorstore()

        relevant_docs = self.vectorstore.similarity_search_with_relevance_scores(query, k=k, score_threshold=score)

        candidates = []
        for doc, relevance_score in relevant_docs:
            user_id = doc.metadata["user_id"]
            print(f"Retrieved (Score: {relevance_score:.3f}): user_id={user_id} about_me={doc.page_content}")
            candidates.append({"id": user_id, "about_me": doc.page_content})

        print(f"{'=' * 100}\n")
        return candidates

    def augment_prompt(self, query: str, context: list[dict[str, Any]]) -> str:
        formatted_context = ""
        for user in context:
            formatted_context += f"USER ID: {user['id']}\n  about_me: {user['about_me']}\n\n"

        return USER_PROMPT.format(context=formatted_context, query=query)

    def generate_grouping(self, augmented_prompt: str) -> list[HobbyGroup]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": augmented_prompt},
        ]

        response = self._llm_client.beta.chat.completions.parse(
            model=_LUNA_MODEL,
            temperature=0.0,
            reasoning_effort="none",
            messages=messages,
            response_format=HobbyGroups,
        )

        return response.choices[0].message.parsed.hobbies

    async def output_grounding(self, hobby_groups: list[HobbyGroup]) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}

        for group in hobby_groups:
            users = []
            for user_id in group.user_ids:
                try:
                    users.append(await self._user_client.get_user(user_id))
                except Exception:
                    print(f"⚠️ Skipping user id={user_id}: not found (likely deleted/hallucinated)")

            if users:
                result[group.hobby] = users

        return result


async def main():
    embeddings = OpenAIEmbeddings(
        model=OPENAI_EMBEDDINGS_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=_EMBEDDINGS_BASE_URL,
        dimensions=384,
    )

    async with HobbySearchWizard(embeddings) as wizard:
        print("Query samples:")
        print(" - I need people who love to go to mountains")
        while True:
            user_question = input("> ").strip()
            if user_question.lower() in ["quit", "exit"]:
                break

            context = await wizard.retrieve_context(user_question)
            if not context:
                print("\n--- No relevant information found ---")
                continue

            augmented_prompt = wizard.augment_prompt(user_question, context)
            hobby_groups = wizard.generate_grouping(augmented_prompt)
            result = await wizard.output_grounding(hobby_groups)

            print(json.dumps(result, indent=2))


asyncio.run(main())

#TODO: Info about app:
# HOBBIES SEARCHING WIZARD
# Searches users by hobbies and provides their full info in JSON format:
#   Input: `I need people who love to go to mountains`
#   Output:
#     ```json
#       "rock climbing": [{full user info JSON},...],
#       "hiking": [{full user info JSON},...],
#       "camping": [{full user info JSON},...]
#     ```
# ---
# 1. Since we are searching hobbies that persist in `about_me` section - we need to embed only user `id` and `about_me`!
#    It will allow us to reduce context window significantly.
# 2. Pay attention that every 5 minutes in User Service will be added new users and some will be deleted. We will at the
#    'cold start' add all users for current moment to vectorstor and with each user request we will update vectorstor on
#    the retrieval step, we will remove deleted users and add new - it will also resolve the issue with consistency
#    within this 2 services and will reduce costs (we don't need on each user request load vectorstor from scratch and pay for it).
# 3. We ask LLM make NEE (Named Entity Extraction) https://cloud.google.com/discover/what-is-entity-extraction?hl=en
#    and provide response in format:
#    {
#       "{hobby}": [{user_id}, 2, 4, 100...]
#    }
#    It allows us to save significant money on generation, reduce time on generation and eliminate possible
#    hallucinations (corrupted personal info or removed some parts of PII (Personal Identifiable Information)). After
#    generation we also need to make output grounding (fetch full info about user and in the same time check that all
#    presented IDs are correct).
# 4. In response we expect JSON with grouped users by their hobbies.
# ---
# This sample is based on the real solution where one Service provides our Wizard with user request, we fetch all
# required data and then returned back to 1st Service response in JSON format.
# ---
# Useful links:
# Chroma DB: https://docs.langchain.com/oss/python/integrations/vectorstores/index#chroma
# Document#id: https://docs.langchain.com/oss/python/langchain/knowledge-base#1-documents-and-document-loaders
# ---
# TASK:
# Implement such application as described on the `flow.png` with adaptive vector based grounding and 'lite' version of
# output grounding (verification that such user exist and fetch full user info)
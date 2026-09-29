from enum import StrEnum
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from commons.constants import OPENAI_API_KEY, OPENAI_HOST
from t6_grounding.user_service_client import UserServiceClient

# The proxy uses DIAL-style deployment routing (same convention as OPENAI_CHAT_COMPLETIONS_ENDPOINT).
# The SDK appends "/chat/completions" itself, so it must not be part of base_url.
_LUNA_MODEL = "gpt-5.6-luna-2026-07-09"
_LUNA_BASE_URL = f"{OPENAI_HOST}/openai/deployments/{_LUNA_MODEL}"

QUERY_ANALYSIS_PROMPT = """You are a query analysis system.

Available search fields: name, surname, email.

Analyze the user question and extract only the values that are explicitly and clearly stated.
Map each extracted value to the appropriate search field. Do not infer, guess, or assume values
that are not directly stated in the question.

Examples:
- "Who is John?" -> name: "John"
- "Find John Smith" -> name: "John", surname: "Smith"

If no explicit values are stated, return an empty list of search parameters.
"""

SYSTEM_PROMPT = """You are a RAG-powered assistant that helps users find information about other users.

## Structure of the User message
`RAG CONTEXT` - Users retrieved from the user database that are relevant to the query.
`USER QUESTION` - The user's actual question.

## Instructions
- Answer ONLY based on the provided `RAG CONTEXT` and the conversation history.
- If `RAG CONTEXT` is empty or does not contain relevant information, state that the question cannot be answered.
- Format user information clearly when presenting it.
"""

USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


class SearchField(StrEnum):
    NAME = "name"
    SURNAME = "surname"
    EMAIL = "email"


class SearchRequest(BaseModel):
    search_field: SearchField = Field(description="Search field")
    search_value: str = Field(description="Search value. Sample: Adam.")


class SearchRequests(BaseModel):
    search_request_parameters: list[SearchRequest] = Field(
        description="List of search parameters to execute",
        default_factory=list
    )


llm_client = OpenAI(api_key=OPENAI_API_KEY, base_url=_LUNA_BASE_URL)

user_client = UserServiceClient()


def retrieve_context(user_question: str) -> list[dict[str, Any]]:
    messages = [
        {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
        {"role": "user", "content": user_question},
    ]

    response = llm_client.beta.chat.completions.parse(
        model=_LUNA_MODEL,
        temperature=0.0,
        reasoning_effort="none",
        messages=messages,
        response_format=SearchRequests,
    )

    parameters = response.choices[0].message.parsed.search_request_parameters

    if parameters:
        search_params = {param.search_field.value: param.search_value for param in parameters}
        print(f"Searching with parameters: {search_params}")
        return user_client.search_users(**search_params)

    print("No specific search parameters found!")
    return []


def augment_prompt(user_question: str, context: list[dict[str, Any]]) -> str:
    formatted_context = ""
    for user in context:
        formatted_context += "User:\n"
        for key, value in user.items():
            formatted_context += f"  {key}: {value}\n"
        formatted_context += "\n"

    augmented_prompt = USER_PROMPT.format(context=formatted_context, query=user_question)
    print(augmented_prompt)
    return augmented_prompt


def generate_answer(augmented_prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": augmented_prompt},
    ]

    response = llm_client.chat.completions.create(
        model=_LUNA_MODEL,
        temperature=0.0,
        reasoning_effort="none",
        messages=messages,
    )

    return response.choices[0].message.content or ""


def main():
    print("Query samples:")
    print(" - I need user emails that filled with hiking and psychology")
    print(" - Who is John?")
    print(" - Find users with surname Adams")
    print(" - Do we have smbd with name John that love painting?")

    while True:
        user_question = input("> ").strip()
        if user_question:
            if user_question.lower() in ['quit', 'exit']:
                break

            print("\n--- Retrieving context ---")
            context = retrieve_context(user_question)

            if context:
                print("\n--- Augmenting prompt ---")
                augmented_prompt = augment_prompt(user_question, context)

                print("\n--- Generating answer ---")
                answer = generate_answer(augmented_prompt)
                print(f"\nAnswer: {answer}\n")
            else:
                print("\n--- No relevant information found ---")


if __name__ == "__main__":
    main()


# The problems with API based Grounding approach are:
#   - We need a Pre-Step to figure out what field should be used for search (Takes time)
#   - Values for search should be correct (✅ John -> ❌ Jonh)
#   - Is not so flexible
# Benefits are:
#   - We fetch actual data (new users added and deleted every 5 minutes)
#   - Costs reduce
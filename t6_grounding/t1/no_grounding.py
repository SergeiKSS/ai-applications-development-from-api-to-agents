import asyncio
from typing import Any

from openai import AsyncOpenAI

from commons.constants import OPENAI_API_KEY, OPENAI_HOST
from t6_grounding.user_service_client import UserServiceClient

# The proxy uses DIAL-style deployment routing (same convention as OPENAI_CHAT_COMPLETIONS_ENDPOINT).
# The SDK appends "/chat/completions" itself, so it must not be part of base_url.
_LUNA_MODEL = "gpt-5.6-luna-2026-07-09"
_LUNA_BASE_URL = f"{OPENAI_HOST}/openai/deployments/{_LUNA_MODEL}"

BATCH_SYSTEM_PROMPT = """You are a user search assistant.

You will be given a list of users and a search question.
- Analyze the search question to determine the search criteria.
- Examine each user in the list and determine whether they match the criteria.
- Return the full details of every matching user, in their original format.
- If no users match, return exactly: NO_MATCHES_FOUND
"""

FINAL_SYSTEM_PROMPT = """You are compiling final user search results.

You will be given several batches of matching users found by earlier searches.
- Review all batch results.
- Combine matching users across batches, removing any duplicates.
- Present the final list of users in a clear, organized manner.
"""

USER_PROMPT = """##USERS:
{context}


##SEARCH QUESTION:
{query}"""


class TokenTracker:

    def __init__(self):
        self.total_tokens = 0
        self.batch_tokens: list[int] = []

    def add_tokens(self, tokens: int):
        self.total_tokens += tokens
        self.batch_tokens.append(tokens)

    def get_summary(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "batch_count": len(self.batch_tokens),
            "batch_tokens": self.batch_tokens,
        }


llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=_LUNA_BASE_URL)

token_tracker = TokenTracker()


def join_context(context: list[dict[str, Any]]) -> str:
    result = ""
    for user in context:
        result += "User:\n"
        for key, value in user.items():
            result += f"  {key}: {value}\n"
        result += "\n"
    return result


async def generate_response(system_prompt: str, user_message: str) -> str:
    print("Processing...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    response = await llm_client.chat.completions.create(
        model=_LUNA_MODEL,
        temperature=0.0,
        reasoning_effort="none",
        messages=messages,
    )

    tokens = response.usage.total_tokens if response.usage else 0
    token_tracker.add_tokens(tokens)

    content = response.choices[0].message.content or ""

    print(f"{content}\n(tokens used: {tokens})")

    return content


async def main():
    print("Query samples:")
    print(" - Do we have someone with name John that loves traveling?")

    user_question = input("> ").strip()

    if user_question:
        # 1. FETCH & BATCH USERS
        print("\n--- Searching user database ---")
        users = UserServiceClient().get_all_users()
        batches = [users[i:i + 100] for i in range(0, len(users), 100)]

        # 2. PARALLEL BATCH SEARCH
        batch_coroutines = [
            generate_response(BATCH_SYSTEM_PROMPT, USER_PROMPT.format(context=join_context(batch), query=user_question))
            for batch in batches
        ]
        batch_results = await asyncio.gather(*batch_coroutines)

        # 3. FILTER RESULTS
        print("\n--- Compiling results ---")
        relevant_results = [result for result in batch_results if result.strip() != "NO_MATCHES_FOUND"]

        # 4. FINAL GENERATION
        print("\n=== SEARCH RESULTS ===")
        if relevant_results:
            combined_results = "\n\n".join(relevant_results)
            await generate_response(FINAL_SYSTEM_PROMPT, USER_PROMPT.format(context=combined_results, query=user_question))
        else:
            print("No users found. Try refining your search.")

        # 5. PRINT PERFORMANCE SUMMARY
        summary = token_tracker.get_summary()
        print(f"\n=== Performance ===\nAPI calls: {summary['batch_count']}\nTotal tokens: {summary['total_tokens']}")


if __name__ == "__main__":
    asyncio.run(main())


# The problems with No Grounding approach are:
#   - If we load whole users as context in one request to LLM we will hit context window
#   - Huge token usage == Higher price per request
#   - Added + one chain in flow where original user data can be changed by LLM (before final generation)
# User Question -> Get all users -> ‼️parallel search of possible candidates‼️ -> probably changed original context -> final generation
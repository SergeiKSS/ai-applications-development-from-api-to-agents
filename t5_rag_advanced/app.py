import os

from commons.constants import OPENAI_API_KEY, OPENAI_CHAT_COMPLETIONS_ENDPOINT, OPENAI_EMBEDDINGS_MODEL, OPENAI_HOST, OPENAI_TERRA_MODEL
from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from t5_rag_advanced.chat.chat_completion_client import ChatCompletionClient
from t5_rag_advanced.embeddings.embeddings_client import EmbeddingsClient
from t5_rag_advanced.embeddings.text_processor import TextProcessor, SearchMode

SYSTEM_PROMPT = """You are a RAG-powered assistant that helps users with questions about microwave usage.

## Structure of the User message
`RAG CONTEXT` - Retrieved chunks from the microwave manual relevant to the query.
`USER QUESTION` - The user's actual question.

## Instructions
- Use information from `RAG CONTEXT` and the prior conversation history when answering `USER QUESTION`.
- Answer ONLY based on `RAG CONTEXT` or the conversation history.
- If the `RAG CONTEXT` is empty or does not contain relevant information, and the conversation history does not
  help either, state that you cannot answer the question.
- Do not answer questions that are not related to microwave usage.
"""

USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MANUAL_PATH = os.path.join(_BASE_DIR, "embeddings", "microwave_manual.txt")

# The proxy uses DIAL-style deployment routing (same convention as OPENAI_CHAT_COMPLETIONS_ENDPOINT).
# The deployment id for embeddings differs from the model name (has a "-1" suffix).
_EMBEDDINGS_ENDPOINT = f"{OPENAI_HOST}/openai/deployments/text-embedding-3-small-1/embeddings"

_DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "vectordb",
    "user": "postgres",
    "password": "postgres",
}

embeddings_client = EmbeddingsClient(endpoint=_EMBEDDINGS_ENDPOINT, model_name=OPENAI_EMBEDDINGS_MODEL, api_key=OPENAI_API_KEY)
chat_completion_client = ChatCompletionClient(endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT, model_name=OPENAI_TERRA_MODEL, api_key=OPENAI_API_KEY)
text_processor = TextProcessor(embeddings_client, _DB_CONFIG)


def main():
    print("Microwave RAG Assistant")

    load_context = input("Load microwave manual into the DB? (y/n): ").strip().lower() == "y"
    if load_context:
        print("Loading and embedding microwave manual...")
        text_processor.process_text_file(
            _MANUAL_PATH,
            chunk_size=300,
            overlap=40,
            dimensions=384,
            truncate=True,
        )
        print("Context loaded.")

    conversation = Conversation()
    conversation.add_message(Message(Role.SYSTEM, SYSTEM_PROMPT))

    while True:
        user_question = input("\n> ").strip()

        # Step 1: Retrieval
        context_chunks = text_processor.search(
            mode=SearchMode.COSINE_DISTANCE,
            request=user_question,
            top_k=5,
            min_score=0.5,
            dimensions=384,
        )
        context = "\n\n".join(context_chunks)

        # Step 2: Augmentation
        augmented_prompt = USER_PROMPT.format(context=context, query=user_question)
        conversation.add_message(Message(Role.USER, augmented_prompt))

        # Step 3: Generation
        answer = chat_completion_client.get_completion(conversation.get_messages())
        conversation.add_message(answer)

        print(f"\n{answer.content}")


main()

# PAY ATTENTION THAT YOU NEED TO RUN Postgres DB ON THE 5433 WITH PGVECTOR EXTENSION!
# RUN docker-compose.yml (or `podman-compose up -d`)

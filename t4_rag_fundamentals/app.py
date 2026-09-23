import os

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr

from commons.constants import OPENAI_API_KEY, OPENAI_EMBEDDINGS_MODEL, OPENAI_TERRA_MODEL

#TODO:
# Create system prompt with:
# - role: explains the role for LLM and what it should do
# - Structure of User message, consists of 2 blocks:
#   - `RAG CONTEXT`: information retrieved on the Retrieval step based on user request
#   - `USER QUESTION`: The user's actual question
# - Instructions:
#   - Model must use only information from conversation
#   - Strictly forbid to answer questions that are not in the conversation or not present in `RAG CONTEXT`
_SYSTEM_PROMPT = """
NEED_TO_IMPLEMENT
"""

_USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


class MicrowaveRAG:

    def __init__(self, embeddings: OpenAIEmbeddings, llm_client: ChatOpenAI):
        self.llm_client = llm_client
        self.embeddings = embeddings
        self.vectorstore = self._setup_vectorstore()

    def _setup_vectorstore(self) -> VectorStore:
        """
        Load existing FAISS index from disk or create a new one.
        Returns:
              VectorStore: Initialized FAISS vectorstore.
        """
        #TODO:
        # - Print a startup message
        # - Check if 'microwave_faiss_index' folder already exists
        # - If yes, load the index from disk using FAISS.load_local()
        # - If no, call _create_new_index() to build and save a fresh index
        # - Return the vectorstore
        raise NotImplementedError

    def _create_new_index(self) -> VectorStore:
        """
        Load the manual, split into chunks, embed, and save a new FAISS index.
        Returns:
              VectorStore: Newly created and saved FAISS vectorstore.
        """
        #TODO:
        # - Load 'microwave_manual.txt' using TextLoader
        # - Split documents into chunks using RecursiveCharacterTextSplitter
        #   (chunk_size=300, chunk_overlap=50, separators=["\n\n", "\n", "."])
        # - Create a FAISS vectorstore from chunks and self.embeddings using FAISS.from_documents()
        # - Save the index locally using vectorstore.save_local("microwave_faiss_index")
        # - Return the vectorstore
        raise NotImplementedError

    def retrieve_context(self, query: str, k: int = 4, score=0.3):
        """
        Retrieve the context for a given query.
        Args:
              query (str): The query to retrieve the context for.
              k (int): The number of relevant documents(chunks) to retrieve.
              score (float): The similarity score between documents and query. Range 0.0 to 1.0.
        """
        #TODO:
        # - Search the vectorstore using similarity_search_with_relevance_scores() with k and score_threshold parameters
        # - Iterate over results, collect each doc's page_content, and print its relevance score
        # - Return all collected chunks joined with "\n\n" as a single context string
        raise NotImplementedError

    def augment_prompt(self, query: str, context: str):
        """
        Inject retrieved context and user query into the prompt template.
        Args:
              query (str): The user's question.
              context (str): Retrieved context from the vectorstore.
        Returns:
              str: Formatted prompt ready for the LLM.
        """
        #TODO:
        # - Format _USER_PROMPT template substituting {context} and {query}
        # - Print the resulting augmented prompt
        # - Return the formatted string
        raise NotImplementedError

    def generate_answer(self, augmented_prompt: str):
        """
        Send the augmented prompt to the LLM and return its response.
        Args:
              augmented_prompt (str): The prompt with injected context and query.
        Returns:
              str: The LLM-generated answer.
        """
        #TODO:
        # - Build a messages list: [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=augmented_prompt)]
        # - Invoke self.llm_client with the messages list
        # - Print the response content
        # - Return the response content string
        raise NotImplementedError


def main(rag: MicrowaveRAG):
    #TODO:
    # - Print a welcome message
    # - Run an infinite loop that reads user input with input()
    # - For each question execute the 3-step RAG pipeline:
    #   - Step 1 (Retrieval):   call rag.retrieve_context() to fetch relevant chunks
    #   - Step 2 (Augmentation): call rag.augment_prompt() to build the prompt
    #   - Step 3 (Generation):  call rag.generate_answer() to get the LLM answer
    raise NotImplementedError


#TODO:
# Start the application by calling main() and passing a MicrowaveRAG instance:
# - Create OpenAIEmbeddings with model=OPENAI_EMBEDDINGS_MODEL and api_key=OPENAI_API_KEY
# - Create ChatOpenAI with temperature=0.0, reasoning_effort="none", model=OPENAI_TERRA_MODEL and api_key=OPENAI_API_KEY
# - Wrap both in a MicrowaveRAG instance and pass it to main()
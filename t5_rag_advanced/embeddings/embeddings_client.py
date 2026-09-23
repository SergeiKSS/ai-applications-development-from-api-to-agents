import json

import requests
from commons.constants import OPENAI_EMBEDDINGS_MODEL




class EmbeddingsClient:
    _endpoint: str
    _api_key: str

    def __init__(self, endpoint: str, model_name: str, api_key: str):
        if not api_key or api_key.strip() == "":
            raise ValueError("API key cannot be null or empty")

        self._endpoint = endpoint
        self._api_key = "Bearer " + api_key
        self._model_name = model_name

    def get_embeddings(
            self, inputs: str | list[str],
            dimensions: int,
            print_response: bool = False
    ) -> dict[int, list[float]]:
        """
        Generate dict of indexed embeddings:
            inputs[0](text) -> [0][embedding]
            inputs[1](text) -> [1][embedding]
            ...

        Args:
            inputs: input text, can be singular string or list of strings
            dimensions: number of dimensions
            print_response: to print response in chat or not
        """
        #TODO:
        # ---
        # https://developers.openai.com/api/reference/resources/embeddings/methods/create
        # ---
        # Provide implementation that will generate embeddings for `inputs` list (don't forget about dimensions) with
        # Embedding model and return back a dict with indexed embeddings (key is index from input list and value vector list)


# Hint:
# Request:
# curl https://api.openai.com/v1/embeddings \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer $OPENAI_API_KEY" \
#   -d '{
#     "input": "Your text string goes here",
#     "model": OPENAI_EMBEDDINGS_MODEL,
#     "dimensions": 384
#   }'
#
#  Response JSON:
#  {
#     "data": [
#         {
#             "embedding": [
#                 0.19686688482761383,
#                 ...
#             ],
#             "index": 0,
#             "object": "embedding"
#         }
#     ],
#     ...
#  }
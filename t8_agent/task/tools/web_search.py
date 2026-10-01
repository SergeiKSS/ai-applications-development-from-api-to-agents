from typing import Any

import requests

from commons.constants import OPENAI_RESPONSES_ENDPOINT, OPENAI_TERRA_MODEL
from t8_agent.task.tools.base import BaseTool


class WebSearchTool(BaseTool):

    def __init__(self, open_ai_api_key: str):
        self.__api_key = f"Bearer {open_ai_api_key}"
        self.__endpoint = OPENAI_RESPONSES_ENDPOINT

    @property
    def name(self) -> str:
        return "web_search_tool"

    @property
    def description(self) -> str:
        return "Tool for WEB searching."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "The search query or question to search for on the web",
                },
            },
            "required": ["request"],
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        headers = {
            "Authorization": self.__api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_TERRA_MODEL,
            "input": arguments["request"],
            "tools": [{"type": "web_search"}],
        }

        response = requests.post(url=self.__endpoint, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            content = "".join(
                item["text"]
                for output in data.get("output", [])
                for item in output.get("content", [])
                if item.get("type") == "output_text"
            )
            return content

        return f"Error: {response.status_code} {response.text}"

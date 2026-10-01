from typing import Any

from t8_agent.task.tools.users.base import BaseUserServiceTool


class SearchUsersTool(BaseUserServiceTool):

    @property
    def name(self) -> str:
        return "search_users"

    @property
    def description(self) -> str:
        return "Searches users by optional filters: name, surname, email, and gender."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "User first name to filter by",
                },
                "surname": {
                    "type": "string",
                    "description": "User surname to filter by",
                },
                "email": {
                    "type": "string",
                    "description": "User email to filter by",
                },
                "gender": {
                    "type": "string",
                    "description": "User gender to filter by",
                },
            },
            "required": [],
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        try:
            return self._user_client.search_users(**arguments)
        except Exception as e:
            return f"Error while searching users: {str(e)}"

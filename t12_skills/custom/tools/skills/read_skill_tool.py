from pathlib import Path
from typing import Any

from t12_skills.custom.file_utils import get_file_content
from t12_skills.custom.tools.base import BaseTool


class ReadSkillTool(BaseTool):
    """Reads files from the local skills directory by path."""

    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir.resolve()

    @property
    def name(self) -> str:
        return "read_skill"

    @property
    def description(self) -> str:
        return (
            "Reads a file from the local skills directory (SKILL.md, scripts, references, assets). "
            "Use it to load a skill's SKILL.md before following its instructions, and to read any "
            "additional file it references. The path is relative to the skills root and must start "
            "with a '/', e.g. path=\"/calculator/SKILL.md\" or path=\"/calculator/scripts/calculate.py\"."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the file to read, relative to the skills root, starting with '/' "
                        "(e.g. '/<skill-name>/SKILL.md' or '/<skill-name>/scripts/<file>')."
                    ),
                }
            },
            "required": ["path"],
        }

    async def _execute(self, arguments: dict[str, Any]) -> str:
        relative_path = arguments["path"].lstrip("/")
        full_path = self._skills_dir / relative_path
        return get_file_content(full_path)
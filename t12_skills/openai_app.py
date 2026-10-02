import io
import json
import zipfile
from pathlib import Path

from openai import OpenAI
from openai.types.responses import ResponseFunctionShellToolCall

from commons.constants import OPENAI_API_KEY, OPENAI_RESPONSES_ENDPOINT, OPENAI_TERRA_MODEL


def zip_skill(skill_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in skill_dir.rglob("*"):
            if path.is_file():
                z.write(path, arcname=path.relative_to(skill_dir.parent))
    buf.seek(0)
    return buf.read()


def get_or_create_skill(skill_name: str, skill_dir: Path, client: OpenAI):
    for skill in client.skills.list():
        if skill.name == skill_name:
            print(f"Found existing skill '{skill_name}': {skill.id}")
            return skill.id

    zip_bytes = zip_skill(skill_dir)
    skill = client.skills.create(files=(f"{skill_dir.name}.zip", zip_bytes, "application/zip"))
    print(f"Created new skill '{skill_name}': {skill.id}")
    return skill.id


def chat(client: OpenAI, skill_id: str, log_request: bool = True, log_response: bool = True):
    previous_response_id = None

    print("\nAgent is ready. Type your query or 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        environment = {
            "type": "container_auto",
            "skills": [{"type": "skill_reference", "skill_id": skill_id}],
        }

        request_payload = {
            "model": OPENAI_TERRA_MODEL,
            "input": [{"role": "user", "content": user_input}],
            "tools": [{"type": "shell", "environment": environment}],
        }
        if previous_response_id:
            request_payload["previous_response_id"] = previous_response_id

        if log_request:
            print(json.dumps(request_payload, indent=2))

        response = client.responses.create(**request_payload)
        previous_response_id = response.id

        if log_response:
            print(json.dumps(response.model_dump(), indent=2, default=str))
        else:
            print(response.output_text)



def delete_skills(client: OpenAI):
    for skill in client.skills.list():
        client.skills.delete(skill.id)
        print(f"Deleted skill '{skill.name}' ({skill.id})")


STYLE_SKILL_NAME= "style-guide"
STYLE_SKILL_DIR = Path(__file__).parent / "_skills" / STYLE_SKILL_NAME

CALCULATOR_SKILL_NAME = "calculator"
CALCULATOR_SKILL_DIR = Path(__file__).parent / "_skills" / CALCULATOR_SKILL_NAME

def main():
    # SDK appends "/responses" itself, so it must not be part of base_url
    base_url = OPENAI_RESPONSES_ENDPOINT.removesuffix("/responses")
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=base_url)

    skill_id = get_or_create_skill(STYLE_SKILL_NAME, STYLE_SKILL_DIR, client)
    try:
        chat(client, skill_id)
    finally:
        delete_skills(client)


if __name__ == "__main__":
    main()
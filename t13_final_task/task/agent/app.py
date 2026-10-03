import logging
import os
import sys
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from t13_final_task.task.agent.clients.http_mcp_client import HttpMcpClient
from t13_final_task.task.agent.clients.stdio_mcp_client import StdioMcpClient
from t13_final_task.task.agent.conversation_manager import ConversationManager
from t13_final_task.task.agent.tools.base import BaseTool
from t13_final_task.task.agent.tools.mcp_tool import McpTool
from t13_final_task.task.agent.tools.read_skill_tool import ReadSkillTool
from t13_final_task.task.agent.ums_agent import UMSAgent
from t13_final_task.task.agent.models import SkillMetadata, load_skills, Message
from commons.constants import OPENAI_API_KEY, OPENAI_TERRA_MODEL

SKILLS_DIR = Path(__file__).parent.parent / "_skills"
UMS_MCP_SERVER_URL = "http://localhost:8005/mcp"
DDG_MCP_DOCKER_IMAGE = "khshanovskyi/ddg-mcp-server:latest"


def _build_available_skills_xml(skills: list[SkillMetadata]) -> str:
    root = ET.Element("available_skills")

    for skill in skills:
        skill_el = ET.SubElement(root, "skill", name=skill.name)

        description_el = ET.SubElement(skill_el, "description")
        description_el.text = skill.description

        if skill.license:
            ET.SubElement(skill_el, "license").text = skill.license

        if skill.compatibility:
            ET.SubElement(skill_el, "compatibility").text = skill.compatibility

        if skill.metadata:
            metadata_el = ET.SubElement(skill_el, "metadata")
            for key, value in skill.metadata.items():
                ET.SubElement(metadata_el, key).text = str(value)

        if skill.allowed_tools:
            ET.SubElement(skill_el, "allowed-tools").text = " ".join(skill.allowed_tools)

    return ET.tostring(root, encoding="unicode")


def build_system_prompt(skills: list[SkillMetadata]) -> str:
    skills_xml = _build_available_skills_xml(skills)
    return (
        "You are an AI assistant with access to Agent Skills — bundles of instructions that extend "
        "your capabilities for specific tasks.\n\n"
        "Available skills:\n"
        f"{skills_xml}\n\n"
        "To use a skill:\n"
        "1. Call `read_skill` with path=\"/<skill-name>/SKILL.md\" to load its instructions.\n"
        "2. Follow the loaded SKILL.md precisely for the rest of the task.\n"
    )


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

conversation_manager: Optional[ConversationManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP clients, Redis, and ConversationManager on startup"""
    global conversation_manager

    skills = load_skills(SKILLS_DIR)
    system_prompt = build_system_prompt(skills)

    tools: list[BaseTool] = [ReadSkillTool(skills_dir=SKILLS_DIR)]

    ums_client = await HttpMcpClient.create(UMS_MCP_SERVER_URL)
    for tool_model in await ums_client.get_tools():
        tools.append(McpTool(client=ums_client, mcp_tool_model=tool_model))

    ddg_client = await StdioMcpClient.create(DDG_MCP_DOCKER_IMAGE)
    for tool_model in await ddg_client.get_tools():
        tools.append(McpTool(client=ddg_client, mcp_tool_model=tool_model))

    ums_agent = UMSAgent(api_key=OPENAI_API_KEY, model=OPENAI_TERRA_MODEL, tools=tools)

    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    await redis_client.ping()

    conversation_manager = ConversationManager(
        ums_agent=ums_agent,
        redis_client=redis_client,
        system_prompt=system_prompt,
    )

    yield

    await redis_client.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: Message
    stream: bool = True


class ChatResponse(BaseModel):
    content: str
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class CreateConversationRequest(BaseModel):
    title: str = None


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "conversation_manager_initialized": conversation_manager is not None
    }

@app.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    return await conversation_manager.create_conversation(request.title)


@app.get("/conversations")
async def list_conversations() -> list[ConversationSummary]:
    return await conversation_manager.list_conversations()


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = await conversation_manager.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    deleted = await conversation_manager.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": f"Conversation '{conversation_id}' deleted"}


@app.post("/conversations/{conversation_id}/chat")
async def chat(conversation_id: str, request: ChatRequest):
    result = await conversation_manager.chat(request.message, conversation_id, stream=request.stream)
    if request.stream:
        return StreamingResponse(result, media_type="text/event-stream")
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8011,
        log_level="debug"
    )
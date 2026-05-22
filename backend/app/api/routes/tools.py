"""Endpoints exposing the agent's tool catalogue."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import ToolsDep

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolDescriptor(BaseModel):
    """Public description of a single registered tool."""

    name: str
    description: str
    parameters: dict[str, object]


class ToolListResponse(BaseModel):
    items: list[ToolDescriptor]
    total: int


@router.get("", response_model=ToolListResponse, summary="List available agent tools")
async def list_tools(tools: ToolsDep) -> ToolListResponse:
    """Return every tool the agent can call, with its parameter schema."""
    items = [
        ToolDescriptor(
            name=schema["function"]["name"],
            description=schema["function"]["description"],
            parameters=schema["function"]["parameters"],
        )
        for schema in tools.openai_schemas()
    ]
    return ToolListResponse(items=items, total=len(items))

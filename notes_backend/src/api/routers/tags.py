from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.db import get_db_session
from src.api.schemas import TagCreate, TagOut, TagUpdate
from src.api import repo

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=List[TagOut],
    summary="List tags",
    description="List tags with optional partial-name filtering.",
    operation_id="list_tags",
)
async def list_tags(
    q: Optional[str] = Query(None, description="Filter tags by name (partial match)."),
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> List[TagOut]:
    """PUBLIC_INTERFACE List tags."""
    async for session in get_db_session(sessionmaker):
        return await repo.list_tags(session, q)


@router.post(
    "",
    response_model=TagOut,
    status_code=201,
    summary="Create tag",
    description="Create a new tag (unique name).",
    operation_id="create_tag",
)
async def create_tag(
    payload: TagCreate,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> TagOut:
    """PUBLIC_INTERFACE Create tag."""
    async for session in get_db_session(sessionmaker):
        return await repo.create_tag(session, payload)


@router.get(
    "/{tag_id}",
    response_model=TagOut,
    summary="Get tag",
    description="Fetch a tag by id.",
    operation_id="get_tag",
)
async def get_tag(
    tag_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> TagOut:
    """PUBLIC_INTERFACE Get tag by id."""
    async for session in get_db_session(sessionmaker):
        return await repo.get_tag(session, tag_id)


@router.patch(
    "/{tag_id}",
    response_model=TagOut,
    summary="Update tag",
    description="Update a tag name (unique).",
    operation_id="update_tag",
)
async def update_tag(
    tag_id: UUID,
    payload: TagUpdate,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> TagOut:
    """PUBLIC_INTERFACE Update tag."""
    async for session in get_db_session(sessionmaker):
        return await repo.update_tag(session, tag_id, payload)


@router.delete(
    "/{tag_id}",
    status_code=204,
    summary="Delete tag",
    description="Delete a tag.",
    operation_id="delete_tag",
)
async def delete_tag(
    tag_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> None:
    """PUBLIC_INTERFACE Delete tag."""
    async for session in get_db_session(sessionmaker):
        await repo.delete_tag(session, tag_id)
        return None

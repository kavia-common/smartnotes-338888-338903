from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.db import get_db_session
from src.api.schemas import NoteCreate, NoteListOut, NoteListQuery, NoteOut, NoteUpdate
from src.api import repo

router = APIRouter(prefix="/notes", tags=["notes"])


def _query_from_params(
    q: Optional[str],
    tag_id: Optional[UUID],
    is_pinned: Optional[bool],
    is_favorite: Optional[bool],
    limit: int,
    offset: int,
    order: str,
) -> NoteListQuery:
    return NoteListQuery(
        q=q,
        tag_id=tag_id,
        is_pinned=is_pinned,
        is_favorite=is_favorite,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get(
    "",
    response_model=NoteListOut,
    summary="List notes",
    description="List notes with optional search and filters (q, tag_id, is_pinned, is_favorite) and pagination.",
    operation_id="list_notes",
)
async def list_notes(
    q: Optional[str] = Query(None, description="Search query (matches title/content)."),
    tag_id: Optional[UUID] = Query(None, description="Filter by tag id."),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned state."),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite state."),
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    order: str = Query("pinned", pattern="^(pinned|updated|created)$", description="Sort order."),
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteListOut:
    """
    PUBLIC_INTERFACE
    List/search notes.

    Returns a stable paginated payload with `items` and `total`.
    """
    async for session in get_db_session(sessionmaker):
        result = await repo.list_notes(session, _query_from_params(q, tag_id, is_pinned, is_favorite, limit, offset, order))
        items = []
        for row in result["items"]:
            note = await repo.get_note(session, row["id"])
            items.append(note)
        return NoteListOut(items=items, total=result["total"])


@router.post(
    "",
    response_model=NoteOut,
    status_code=201,
    summary="Create note",
    description="Create a new note and optionally associate tags.",
    operation_id="create_note",
)
async def create_note(
    payload: NoteCreate,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteOut:
    """PUBLIC_INTERFACE Create a note."""
    async for session in get_db_session(sessionmaker):
        return await repo.create_note(session, payload)


@router.get(
    "/{note_id}",
    response_model=NoteOut,
    summary="Get note",
    description="Fetch a note by id.",
    operation_id="get_note",
)
async def get_note(
    note_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteOut:
    """PUBLIC_INTERFACE Get a note by id."""
    async for session in get_db_session(sessionmaker):
        return await repo.get_note(session, note_id)


@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update note",
    description="Update note fields and optionally replace tag associations.",
    operation_id="update_note",
)
async def update_note(
    note_id: UUID,
    payload: NoteUpdate,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteOut:
    """PUBLIC_INTERFACE Update a note."""
    async for session in get_db_session(sessionmaker):
        return await repo.update_note(session, note_id, payload)


@router.delete(
    "/{note_id}",
    status_code=204,
    summary="Delete note",
    description="Delete a note.",
    operation_id="delete_note",
)
async def delete_note(
    note_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> None:
    """PUBLIC_INTERFACE Delete a note."""
    async for session in get_db_session(sessionmaker):
        await repo.delete_note(session, note_id)
        return None


@router.post(
    "/{note_id}/pin",
    response_model=NoteOut,
    summary="Pin note",
    description="Set is_pinned=true and pinned_at=now().",
    operation_id="pin_note",
)
async def pin_note(
    note_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteOut:
    """PUBLIC_INTERFACE Pin a note."""
    async for session in get_db_session(sessionmaker):
        return await repo.set_note_pinned(session, note_id, True)


@router.post(
    "/{note_id}/unpin",
    response_model=NoteOut,
    summary="Unpin note",
    description="Set is_pinned=false and pinned_at=NULL.",
    operation_id="unpin_note",
)
async def unpin_note(
    note_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(),
) -> NoteOut:
    """PUBLIC_INTERFACE Unpin a note."""
    async for session in get_db_session(sessionmaker):
        return await repo.set_note_pinned(session, note_id, False)

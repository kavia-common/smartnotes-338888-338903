from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import ApiException
from src.api.schemas import NoteCreate, NoteListQuery, NoteOut, TagCreate, TagOut, TagUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _fetch_tags_for_note(session: AsyncSession, note_id: UUID) -> List[TagOut]:
    rows = (
        await session.execute(
            text(
                """
                SELECT t.id, t.name, t.created_at, t.updated_at
                FROM tags t
                JOIN note_tags nt ON nt.tag_id = t.id
                WHERE nt.note_id = :note_id
                ORDER BY t.name ASC
                """
            ),
            {"note_id": note_id},
        )
    ).mappings().all()
    return [TagOut(**dict(r)) for r in rows]


def _note_row_to_out(note_row: Dict[str, Any], tags: List[TagOut]) -> NoteOut:
    return NoteOut(tags=tags, **note_row)


# PUBLIC_INTERFACE
async def create_tag(session: AsyncSession, payload: TagCreate) -> TagOut:
    """Create a tag; raises 409 if name already exists."""
    try:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO tags (name)
                    VALUES (:name)
                    RETURNING id, name, created_at, updated_at
                    """
                ),
                {"name": payload.name},
            )
        ).mappings().one()
        await session.commit()
        return TagOut(**dict(row))
    except IntegrityError as e:
        await session.rollback()
        raise ApiException(status_code=409, code="TAG_ALREADY_EXISTS", message="Tag name already exists") from e


# PUBLIC_INTERFACE
async def list_tags(session: AsyncSession, q: Optional[str]) -> List[TagOut]:
    """List tags, optionally filtered by partial name match."""
    if q:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, name, created_at, updated_at
                    FROM tags
                    WHERE name ILIKE '%' || :q || '%'
                    ORDER BY name ASC
                    """
                ),
                {"q": q},
            )
        ).mappings().all()
    else:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, name, created_at, updated_at
                    FROM tags
                    ORDER BY name ASC
                    """
                )
            )
        ).mappings().all()
    return [TagOut(**dict(r)) for r in rows]


# PUBLIC_INTERFACE
async def get_tag(session: AsyncSession, tag_id: UUID) -> TagOut:
    """Get a tag by id; raises 404 if missing."""
    row = (
        await session.execute(
            text(
                """
                SELECT id, name, created_at, updated_at
                FROM tags
                WHERE id = :id
                """
            ),
            {"id": tag_id},
        )
    ).mappings().first()
    if not row:
        raise ApiException(status_code=404, code="TAG_NOT_FOUND", message="Tag not found")
    return TagOut(**dict(row))


# PUBLIC_INTERFACE
async def update_tag(session: AsyncSession, tag_id: UUID, payload: TagUpdate) -> TagOut:
    """Update tag name; raises 404 if missing and 409 if name conflicts."""
    try:
        row = (
            await session.execute(
                text(
                    """
                    UPDATE tags
                    SET name = :name
                    WHERE id = :id
                    RETURNING id, name, created_at, updated_at
                    """
                ),
                {"id": tag_id, "name": payload.name},
            )
        ).mappings().first()
        if not row:
            await session.rollback()
            raise ApiException(status_code=404, code="TAG_NOT_FOUND", message="Tag not found")
        await session.commit()
        return TagOut(**dict(row))
    except IntegrityError as e:
        await session.rollback()
        raise ApiException(status_code=409, code="TAG_ALREADY_EXISTS", message="Tag name already exists") from e


# PUBLIC_INTERFACE
async def delete_tag(session: AsyncSession, tag_id: UUID) -> None:
    """Delete a tag (cascades join rows); raises 404 if missing."""
    res = await session.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag_id})
    if res.rowcount == 0:
        await session.rollback()
        raise ApiException(status_code=404, code="TAG_NOT_FOUND", message="Tag not found")
    await session.commit()


async def _ensure_tag_ids_exist(session: AsyncSession, tag_ids: List[UUID]) -> None:
    if not tag_ids:
        return
    rows = (
        await session.execute(
            text("SELECT id FROM tags WHERE id = ANY(:ids)"),
            {"ids": tag_ids},
        )
    ).all()
    existing = {r[0] for r in rows}
    missing = [str(tid) for tid in tag_ids if tid not in existing]
    if missing:
        raise ApiException(
            status_code=400,
            code="INVALID_TAG_IDS",
            message="One or more tag_ids do not exist",
            details={"missing_tag_ids": missing},
        )


async def _replace_note_tags(session: AsyncSession, note_id: UUID, tag_ids: List[UUID]) -> None:
    await session.execute(text("DELETE FROM note_tags WHERE note_id = :note_id"), {"note_id": note_id})
    for tag_id in tag_ids:
        await session.execute(
            text(
                """
                INSERT INTO note_tags (note_id, tag_id)
                VALUES (:note_id, :tag_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"note_id": note_id, "tag_id": tag_id},
        )


# PUBLIC_INTERFACE
async def create_note(session: AsyncSession, payload: NoteCreate) -> NoteOut:
    """Create a note and associate tags (if provided)."""
    await _ensure_tag_ids_exist(session, payload.tag_ids)

    note_row = (
        await session.execute(
            text(
                """
                INSERT INTO notes (title, content, is_pinned, pinned_at, is_favorite)
                VALUES (:title, :content, :is_pinned, :pinned_at, :is_favorite)
                RETURNING id, title, content, is_pinned, pinned_at, is_favorite, created_at, updated_at
                """
            ),
            {
                "title": payload.title,
                "content": payload.content,
                "is_pinned": payload.is_pinned,
                "pinned_at": _utcnow() if payload.is_pinned else None,
                "is_favorite": payload.is_favorite,
            },
        )
    ).mappings().one()

    await _replace_note_tags(session, note_row["id"], payload.tag_ids)
    await session.commit()

    tags = await _fetch_tags_for_note(session, note_row["id"])
    return _note_row_to_out(dict(note_row), tags)


# PUBLIC_INTERFACE
async def get_note(session: AsyncSession, note_id: UUID) -> NoteOut:
    """Fetch a note by id; raises 404 if missing."""
    note_row = (
        await session.execute(
            text(
                """
                SELECT id, title, content, is_pinned, pinned_at, is_favorite, created_at, updated_at
                FROM notes
                WHERE id = :id AND deleted_at IS NULL
                """
            ),
            {"id": note_id},
        )
    ).mappings().first()
    if not note_row:
        raise ApiException(status_code=404, code="NOTE_NOT_FOUND", message="Note not found")

    tags = await _fetch_tags_for_note(session, note_id)
    return _note_row_to_out(dict(note_row), tags)


async def _note_exists(session: AsyncSession, note_id: UUID) -> bool:
    row = (
        await session.execute(
            text("SELECT 1 FROM notes WHERE id = :id AND deleted_at IS NULL"),
            {"id": note_id},
        )
    ).first()
    return row is not None


# PUBLIC_INTERFACE
async def update_note(session: AsyncSession, note_id: UUID, payload: Any) -> NoteOut:
    """
    Update a note fields and optionally replace tags.

    payload is expected to be NoteUpdate, but kept Any to avoid circular imports in this module.
    """
    if not await _note_exists(session, note_id):
        raise ApiException(status_code=404, code="NOTE_NOT_FOUND", message="Note not found")

    updates: Dict[str, Any] = {}
    for field in ("title", "content", "is_favorite", "is_pinned"):
        value = getattr(payload, field, None)
        if value is not None:
            updates[field] = value

    if "is_pinned" in updates:
        updates["pinned_at"] = _utcnow() if updates["is_pinned"] else None

    # Build SQL dynamically but safely via explicit column allowlist.
    if updates:
        set_fragments = ", ".join([f"{col} = :{col}" for col in updates.keys()])
        params = {"id": note_id, **updates}
        note_row = (
            await session.execute(
                text(
                    f"""
                    UPDATE notes
                    SET {set_fragments}
                    WHERE id = :id
                    RETURNING id, title, content, is_pinned, pinned_at, is_favorite, created_at, updated_at
                    """
                ),
                params,
            )
        ).mappings().one()
    else:
        note_row = (
            await session.execute(
                text(
                    """
                    SELECT id, title, content, is_pinned, pinned_at, is_favorite, created_at, updated_at
                    FROM notes
                    WHERE id = :id
                    """
                ),
                {"id": note_id},
            )
        ).mappings().one()

    tag_ids = getattr(payload, "tag_ids", None)
    if tag_ids is not None:
        await _ensure_tag_ids_exist(session, tag_ids)
        await _replace_note_tags(session, note_id, tag_ids)

    await session.commit()
    tags = await _fetch_tags_for_note(session, note_id)
    return _note_row_to_out(dict(note_row), tags)


# PUBLIC_INTERFACE
async def delete_note(session: AsyncSession, note_id: UUID) -> None:
    """Hard-delete a note (join rows cascade)."""
    res = await session.execute(text("DELETE FROM notes WHERE id = :id"), {"id": note_id})
    if res.rowcount == 0:
        await session.rollback()
        raise ApiException(status_code=404, code="NOTE_NOT_FOUND", message="Note not found")
    await session.commit()


def _order_by_clause(order: str) -> str:
    if order == "updated":
        return "n.updated_at DESC"
    if order == "created":
        return "n.created_at DESC"
    # default pinned order: pinned first, pinned_at desc, then updated
    return "n.is_pinned DESC, n.pinned_at DESC NULLS LAST, n.updated_at DESC"


# PUBLIC_INTERFACE
async def list_notes(session: AsyncSession, query: NoteListQuery) -> Dict[str, Any]:
    """
    List/search notes with filters.

    Returns:
      {"items": [note rows as dict], "total": int}
    """
    where = ["n.deleted_at IS NULL"]
    params: Dict[str, Any] = {"limit": query.limit, "offset": query.offset}

    if query.q:
        where.append("(n.title ILIKE '%' || :q || '%' OR n.content ILIKE '%' || :q || '%')")
        params["q"] = query.q

    if query.is_pinned is not None:
        where.append("n.is_pinned = :is_pinned")
        params["is_pinned"] = query.is_pinned

    if query.is_favorite is not None:
        where.append("n.is_favorite = :is_favorite")
        params["is_favorite"] = query.is_favorite

    join = ""
    if query.tag_id:
        join = "JOIN note_tags nt_filter ON nt_filter.note_id = n.id"
        where.append("nt_filter.tag_id = :tag_id")
        params["tag_id"] = query.tag_id

    where_sql = " AND ".join(where)
    order_by_sql = _order_by_clause(query.order)

    total = (
        await session.execute(
            text(
                f"""
                SELECT COUNT(DISTINCT n.id)
                FROM notes n
                {join}
                WHERE {where_sql}
                """
            ),
            params,
        )
    ).scalar_one()

    rows = (
        await session.execute(
            text(
                f"""
                SELECT DISTINCT n.id, n.title, n.content, n.is_pinned, n.pinned_at, n.is_favorite, n.created_at, n.updated_at
                FROM notes n
                {join}
                WHERE {where_sql}
                ORDER BY {order_by_sql}
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()

    items = [dict(r) for r in rows]
    return {"items": items, "total": int(total)}


# PUBLIC_INTERFACE
async def set_note_pinned(session: AsyncSession, note_id: UUID, is_pinned: bool) -> NoteOut:
    """Pin/unpin a note (sets pinned_at accordingly)."""
    pinned_at = _utcnow() if is_pinned else None
    note_row = (
        await session.execute(
            text(
                """
                UPDATE notes
                SET is_pinned = :is_pinned,
                    pinned_at = :pinned_at
                WHERE id = :id
                RETURNING id, title, content, is_pinned, pinned_at, is_favorite, created_at, updated_at
                """
            ),
            {"id": note_id, "is_pinned": is_pinned, "pinned_at": pinned_at},
        )
    ).mappings().first()
    if not note_row:
        await session.rollback()
        raise ApiException(status_code=404, code="NOTE_NOT_FOUND", message="Note not found")
    await session.commit()
    tags = await _fetch_tags_for_note(session, note_id)
    return _note_row_to_out(dict(note_row), tags)

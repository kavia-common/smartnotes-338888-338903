from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Tag name (unique, case-sensitive).")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tag name must not be empty")
        return v


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="New tag name (unique, case-sensitive).")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tag name must not be empty")
        return v


class TagOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class NoteBase(BaseModel):
    title: str = Field("", max_length=200, description="Note title.")
    content: str = Field("", description="Note content (plain text).")
    is_favorite: bool = Field(False, description="Whether the note is marked as favorite.")
    is_pinned: bool = Field(False, description="Whether the note is pinned.")
    tag_ids: List[UUID] = Field(default_factory=list, description="Tags to associate with this note.")

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        # Title may be empty per schema default, but should be normalized.
        return v.strip()

    @field_validator("content")
    @classmethod
    def normalize_content(cls, v: str) -> str:
        # Keep content as-is except ensure it is a string.
        return v if v is not None else ""


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Updated title.")
    content: Optional[str] = Field(None, description="Updated content.")
    is_favorite: Optional[bool] = Field(None, description="Updated favorite flag.")
    is_pinned: Optional[bool] = Field(None, description="Updated pinned flag.")
    tag_ids: Optional[List[UUID]] = Field(None, description="Replace tag associations with these tags.")

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class NoteOut(BaseModel):
    id: UUID
    title: str
    content: str
    is_pinned: bool
    pinned_at: Optional[datetime]
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    tags: List[TagOut] = Field(default_factory=list)


class NoteListOut(BaseModel):
    items: List[NoteOut]
    total: int


class NoteListQuery(BaseModel):
    q: Optional[str] = Field(None, description="Search query (matches title/content via ILIKE).")
    tag_id: Optional[UUID] = Field(None, description="Filter notes having a specific tag.")
    is_pinned: Optional[bool] = Field(None, description="Filter by pinned state.")
    is_favorite: Optional[bool] = Field(None, description="Filter by favorite state.")
    limit: int = Field(50, ge=1, le=200, description="Max number of notes to return.")
    offset: int = Field(0, ge=0, description="Offset for pagination.")
    order: str = Field(
        "pinned",
        description="Sort order: 'pinned' (default), 'updated', 'created'.",
        pattern="^(pinned|updated|created)$",
    )

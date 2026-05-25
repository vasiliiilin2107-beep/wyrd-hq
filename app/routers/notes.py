from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import get_session
from ..models import Note

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreate(BaseModel):
    text: str


@router.get("")
async def list_notes(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Note).order_by(Note.created_at.desc()))
    return [{"id": n.id, "text": n.text, "created_at": n.created_at} for n in result.scalars().all()]


@router.post("")
async def create_note(data: NoteCreate, session: AsyncSession = Depends(get_session)):
    note = Note(text=data.text)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return {"id": note.id, "text": note.text, "created_at": note.created_at}


@router.delete("/{note_id}")
async def delete_note(note_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if note:
        await session.delete(note)
        await session.commit()
    return {"ok": True}

"""Base CRUD class for async SQLAlchemy operations."""

from typing import Any, Generic, TypeVar, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        return await db.get(self.model, id)

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, **kwargs: Any) -> ModelType:
        obj = self.model(**kwargs)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, id: int, **kwargs: Any) -> ModelType | None:
        obj = await self.get(db, id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, id: int) -> bool:
        obj = await self.get(db, id)
        if not obj:
            return False
        await db.delete(obj)
        await db.commit()
        return True

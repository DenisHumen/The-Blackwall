"""Firewall rules management: CRUD operations and stats."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleUpdate, RuleResponse, RuleStats
from app.crud.rule import crud_rule

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/stats", response_model=RuleStats)
async def rule_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard widget: aggregated firewall statistics."""
    return await crud_rule.get_stats(db)


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await crud_rule.get_all(db, skip=skip, limit=limit)


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule: RuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if rule.action not in ("accept", "drop", "reject"):
        raise HTTPException(400, "action must be accept, drop, or reject")
    if rule.direction not in ("in", "out", "forward"):
        raise HTTPException(400, "direction must be in, out, or forward")
    return await crud_rule.create(
        db, **rule.model_dump(), created_by=user.username
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = await crud_rule.get(db, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await crud_rule.get(db, rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")
    if existing.is_system:
        raise HTTPException(403, "Cannot modify system rules")
    updated = await crud_rule.update(
        db, rule_id, **data.model_dump(exclude_unset=True)
    )
    return updated


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await crud_rule.get(db, rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")
    if existing.is_system:
        raise HTTPException(403, "Cannot delete system rules")
    await crud_rule.delete(db, rule_id)

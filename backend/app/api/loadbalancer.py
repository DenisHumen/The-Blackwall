"""Load Balancer management API — CRUD, gateways, health checks, activation."""

import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, SessionLocal
from app.core.auth import get_current_user
from app.models.user import User
from app.models.loadbalancer import LoadBalancerConfig, Gateway
from app.schemas.loadbalancer import (
    LoadBalancerCreate,
    LoadBalancerUpdate,
    LoadBalancerResponse,
    LoadBalancerStatus,
    GatewayCreate,
    GatewayResponse,
)
from app.core.loadbalancer import (
    activate_balancer,
    deactivate_balancer,
    create_virtual_interface,
    destroy_virtual_interface,
    interface_exists,
    ping_check,
    get_active_engines,
    detect_interface,
    enable_ip_forwarding,
)

router = APIRouter(prefix="/api/loadbalancer", tags=["loadbalancer"])

_VALID_MODES = ("round_robin", "failover")


# ---------------------------------------------------------------------------
# Load Balancer CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[LoadBalancerResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(LoadBalancerConfig))
    return result.scalars().all()


@router.get("/{config_id}", response_model=LoadBalancerResponse)
async def get_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return cfg


@router.post("", response_model=LoadBalancerResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    data: LoadBalancerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.mode not in _VALID_MODES:
        raise HTTPException(status_code=400, detail="Mode must be 'round_robin' or 'failover'")

    cfg = LoadBalancerConfig(
        name=data.name,
        mode=data.mode,
        use_virtual_interface=data.use_virtual_interface,
        virtual_ip=data.virtual_ip,
        virtual_interface=data.virtual_interface,
        check_interval=data.check_interval,
        check_target=data.check_target,
        check_timeout=data.check_timeout,
        check_failures=data.check_failures,
    )
    db.add(cfg)
    await db.flush()

    for gw_data in data.gateways:
        gw = Gateway(
            lb_config_id=cfg.id,
            address=gw_data.address,
            interface_name=gw_data.interface_name,
            weight=gw_data.weight,
            priority=gw_data.priority,
            is_primary=gw_data.is_primary,
        )
        db.add(gw)

    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.patch("/{config_id}", response_model=LoadBalancerResponse)
async def update_config(
    config_id: int,
    data: LoadBalancerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    if data.mode is not None and data.mode not in _VALID_MODES:
        raise HTTPException(status_code=400, detail="Mode must be 'round_robin' or 'failover'")

    update_fields = data.model_dump(exclude_none=True)

    # Handle activation / deactivation
    if "is_active" in update_fields:
        if update_fields["is_active"] and not cfg.is_active:
            # Activating
            await _activate_config(cfg)
        elif not update_fields["is_active"] and cfg.is_active:
            # Deactivating
            await _deactivate_config(cfg)

    for field, value in update_fields.items():
        setattr(cfg, field, value)

    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    if cfg.is_active:
        await _deactivate_config(cfg)
    await db.delete(cfg)
    await db.commit()


# ---------------------------------------------------------------------------
# Activation / deactivation helpers
# ---------------------------------------------------------------------------

async def _activate_config(cfg: LoadBalancerConfig):
    """Enable IP forwarding, create virtual interface (if enabled), start engine."""
    await enable_ip_forwarding()
    if cfg.use_virtual_interface and cfg.virtual_interface and cfg.virtual_ip:
        await create_virtual_interface(cfg.virtual_interface, cfg.virtual_ip)
    await activate_balancer(cfg.id, SessionLocal)


async def _deactivate_config(cfg: LoadBalancerConfig):
    """Stop the balancer engine and destroy virtual interface (if enabled)."""
    await deactivate_balancer(cfg.id)
    if cfg.use_virtual_interface and cfg.virtual_interface:
        await destroy_virtual_interface(cfg.virtual_interface)


# ---------------------------------------------------------------------------
# Status & control
# ---------------------------------------------------------------------------

@router.get("/{config_id}/status", response_model=LoadBalancerStatus)
async def get_status(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed runtime status of a load balancer."""
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    iface_up = await interface_exists(cfg.virtual_interface)

    active_gw = None
    if cfg.active_gateway_id:
        for gw in cfg.gateways:
            if gw.id == cfg.active_gateway_id:
                active_gw = gw
                break

    return LoadBalancerStatus(
        id=cfg.id,
        name=cfg.name,
        mode=cfg.mode,
        is_active=cfg.is_active,
        virtual_interface=cfg.virtual_interface,
        virtual_ip=cfg.virtual_ip,
        interface_exists=iface_up,
        active_gateway=active_gw,
        gateways=cfg.gateways,
        switch_count=cfg.switch_count,
        last_switch=cfg.last_switch,
    )


# ---------------------------------------------------------------------------
# Gateway management
# ---------------------------------------------------------------------------

@router.post("/{config_id}/gateways", response_model=GatewayResponse, status_code=status.HTTP_201_CREATED)
async def add_gateway(
    config_id: int,
    data: GatewayCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    gw = Gateway(
        lb_config_id=config_id,
        address=data.address,
        interface_name=data.interface_name,
        weight=data.weight,
        priority=data.priority,
        is_primary=data.is_primary,
    )
    db.add(gw)
    await db.commit()
    await db.refresh(gw)
    return gw


@router.delete("/{config_id}/gateways/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_gateway(
    config_id: int,
    gateway_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    gw = await db.get(Gateway, gateway_id)
    if not gw or gw.lb_config_id != config_id:
        raise HTTPException(status_code=404, detail="Gateway not found")
    await db.delete(gw)
    await db.commit()


# ---------------------------------------------------------------------------
# Health check (manual trigger)
# ---------------------------------------------------------------------------

@router.post("/{config_id}/health-check", response_model=list[GatewayResponse])
async def health_check(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run a manual one-time health check on all gateways."""
    cfg = await db.get(LoadBalancerConfig, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    now = datetime.now(timezone.utc)
    tasks = [
        ping_check(gw.address, cfg.check_target, cfg.check_timeout or 2.0)
        for gw in cfg.gateways
    ]
    results = await asyncio.gather(*tasks)

    for gw, (is_healthy, latency_ms) in zip(cfg.gateways, results):
        gw.is_healthy = is_healthy
        gw.latency_ms = latency_ms
        gw.last_check = now

    await db.commit()
    await db.refresh(cfg)
    return cfg.gateways

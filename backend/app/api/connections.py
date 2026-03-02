from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.connectors import get_connector_for_connection
from app.database import get_db
from app.models.connection import Connection
from app.models.organization import Organization
from app.models.user import User
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResult,
    ConnectionUpdate,
)

router = APIRouter(tags=["connections"])


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    payload: ConnectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new warehouse connection."""
    # Get the user's organization
    result = await db.execute(select(Organization).where(Organization.owner_id == user.id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=400, detail="No organization found for user")

    # MVP: store credentials reference as a placeholder
    # Production: store in AWS Secrets Manager and save the ARN
    credentials_ref = f"local://{org.id}/{payload.name}"

    # Merge credentials into config so the connector factory can find them
    merged_config = {**(payload.config or {}), **payload.credentials}

    connection = Connection(
        org_id=org.id,
        type=payload.type,
        name=payload.name,
        credentials_ref=credentials_ref,
        config=merged_config,
        status="pending",
    )
    db.add(connection)
    await db.flush()
    await db.refresh(connection)
    return connection


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connection credentials and return status."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        connector = get_connector_for_connection(connection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # SDK not installed or other init error — return as test failure
        now = datetime.now(timezone.utc)
        connection.status = "failed"
        connection.last_tested_at = now
        return ConnectionTestResult(
            success=False,
            message="Connection test failed",
            error_detail=str(e),
            tested_at=now,
        )

    now = datetime.now(timezone.utc)

    error_detail = None
    try:
        success = await connector.test_connection()
    except Exception as e:
        success = False
        error_detail = str(e)

    connection.status = "active" if success else "failed"
    connection.last_tested_at = now

    message = "Connection test successful" if success else "Connection test failed"
    return ConnectionTestResult(
        success=success,
        message=message,
        error_detail=error_detail,
        tested_at=now,
    )


@router.get("/connections/{connection_id}/tables")
async def list_tables(
    connection_id: UUID,
    schema: str = Query(..., description="Schema name to list tables from"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available tables from the connected warehouse."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        connector = get_connector_for_connection(connection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        tables = await connector.get_tables(schema)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve tables from warehouse: {e}",
        )

    return {"tables": tables}


@router.get("/connections", response_model=list[ConnectionResponse])
async def list_connections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connections for the user's organization."""
    result = await db.execute(select(Organization).where(Organization.owner_id == user.id))
    org = result.scalar_one_or_none()
    if not org:
        return []

    result = await db.execute(
        select(Connection)
        .where(Connection.org_id == org.id)
        .order_by(Connection.created_at.desc())
    )
    return result.scalars().all()


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single connection by ID."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.patch("/connections/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: UUID,
    payload: ConnectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a connection's name, credentials, or config."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    if payload.name is not None:
        connection.name = payload.name
    if payload.credentials is not None or payload.config is not None:
        current_config = connection.config or {}
        if payload.credentials is not None:
            current_config.update(payload.credentials)
        if payload.config is not None:
            current_config.update(payload.config)
        connection.config = current_config
        connection.status = "pending"

    await db.flush()
    await db.refresh(connection)
    return connection


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a connection and its monitored tables."""
    result = await db.execute(
        select(Connection)
        .where(Connection.id == connection_id)
        .options(selectinload(Connection.monitored_tables))
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Delete associated monitored tables first
    for table in connection.monitored_tables:
        await db.delete(table)

    await db.delete(connection)
    await db.flush()

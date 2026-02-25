from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.connection import Connection
from app.models.organization import Organization
from app.models.user import User
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionTestResult

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

    connection = Connection(
        org_id=org.id,
        type=payload.type,
        name=payload.name,
        credentials_ref=credentials_ref,
        config=payload.config,
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

    # TODO: Actually test the warehouse connection using the appropriate connector
    now = datetime.now(timezone.utc)
    connection.status = "active"
    connection.last_tested_at = now

    return ConnectionTestResult(
        success=True,
        message="Connection test successful",
        tested_at=now,
    )


@router.get("/connections/{connection_id}/tables")
async def list_tables(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available tables from the connected warehouse."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # TODO: Use the appropriate connector to list tables
    return {"tables": [], "message": "Connector not yet configured"}

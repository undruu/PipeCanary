from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.connectors import get_connector_for_connection
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

    now = datetime.now(timezone.utc)

    try:
        success = await connector.test_connection()
    except Exception:
        success = False

    connection.status = "active" if success else "failed"
    connection.last_tested_at = now

    message = "Connection test successful" if success else "Connection test failed"
    return ConnectionTestResult(
        success=success,
        message=message,
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

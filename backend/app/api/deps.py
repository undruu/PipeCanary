from uuid import UUID

from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User


async def get_current_user(
    authorization: str = Header(..., description="Bearer token or API key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header.

    MVP: Accepts a user UUID directly for development.
    Production: Will validate JWT tokens from Clerk/Auth0.
    """
    token = authorization.removeprefix("Bearer ").strip()

    try:
        user_id = UUID(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

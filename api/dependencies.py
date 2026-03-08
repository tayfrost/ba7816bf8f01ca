from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import async_session_factory
from api.models.company import Company
from api.models.company_role import SaasCompanyRole
from api.models.user import SaasUserData

security = HTTPBearer()
ALGORITHM = "HS256"


@dataclass
class CurrentUser:
    """Lightweight representation of the authenticated user + company context."""
    user_id: int
    company_id: int
    role: str
    name: str
    surname: str
    email: str


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        company_id: int = payload.get("company_id")
        role: str = payload.get("role")
        if user_id_str is None or company_id is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(user_id_str)

    # Verify user exists
    user = await db.get(SaasUserData, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Verify company role is still active
    result = await db.execute(
        select(SaasCompanyRole).where(
            SaasCompanyRole.company_id == company_id,
            SaasCompanyRole.user_id == user_id,
            SaasCompanyRole.role == role,
            SaasCompanyRole.status == "active",
        )
    )
    company_role = result.scalar_one_or_none()
    if not company_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Role no longer active")

    # Check company is not soft-deleted
    company = await db.get(Company, company_id)
    if not company or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company deleted")

    return CurrentUser(
        user_id=user_id,
        company_id=company_id,
        role=role,
        name=user.name,
        surname=user.surname,
        email=user.email,
    )


def require_role(*roles: str) -> Callable:
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized. Required: {', '.join(roles)}",
            )
        return user
    return role_checker

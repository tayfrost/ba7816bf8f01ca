import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from api.config import settings
from database.db_service.utils import companies_crud, crud_auth_users
from database.db_service.utils import users_crud

security = HTTPBearer()
ALGORITHM = "HS256"


@dataclass
class CurrentUser:
    user_id: uuid.UUID
    company_id: int
    role: str
    display_name: str | None
    email: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await asyncio.to_thread(users_crud.get_user_by_id, company_id, user_id)
    if not user or user.status != "active" or user.role != role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    company = await asyncio.to_thread(companies_crud.get_company_by_id, company_id)
    if not company or company.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company deleted")

    auth_user = await asyncio.to_thread(crud_auth_users.get_auth_user_by_user_id, company_id, user_id)
    email = auth_user.email if auth_user else ""

    return CurrentUser(
        user_id=user_id,
        company_id=company_id,
        role=role,
        display_name=user.display_name,
        email=email,
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

import asyncio
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from api.config import settings
from database.services import companies_crud, crud_auth_users, subscriptions_crud
from database.services import users_crud

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def register_user(
    email: str,
    password: str,
    display_name: str | None,
    company_name: str,
    plan_id: int = 1,
) -> str:
    # 1. Create company
    company = await asyncio.to_thread(companies_crud.create_company, company_name)

    # 2. Create subscription (trial, 30 days)
    now = datetime.now(timezone.utc)
    await asyncio.to_thread(
        subscriptions_crud.create_subscription,
        company.company_id,
        plan_id,
        status="trialing",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )

    # 3. Create user (biller role)
    user = await asyncio.to_thread(
        users_crud.create_user,
        company.company_id,
        role="biller",
        status="active",
        display_name=display_name,
    )

    # 4. Create auth_user (email + password hash)
    await asyncio.to_thread(
        crud_auth_users.create_auth_user,
        company.company_id,
        email=email.lower().strip(),
        password_hash=hash_password(password),
        user_id=user.user_id,
    )

    return create_access_token(
        {"sub": str(user.user_id), "company_id": company.company_id, "role": "biller"}
    )


async def login_user(email: str, password: str) -> str | None:
    auth_user = await asyncio.to_thread(
        crud_auth_users.get_auth_user_by_email, email.lower().strip()
    )
    if not auth_user or not verify_password(password, auth_user.password_hash):
        return None

    if not auth_user.user_id:
        return None

    user = await asyncio.to_thread(
        users_crud.get_user_by_id, auth_user.company_id, auth_user.user_id
    )
    if not user or user.status != "active":
        return None

    company = await asyncio.to_thread(
        companies_crud.get_company_by_id, auth_user.company_id
    )
    if not company or company.deleted_at is not None:
        return None

    return create_access_token(
        {"sub": str(user.user_id), "company_id": auth_user.company_id, "role": user.role}
    )

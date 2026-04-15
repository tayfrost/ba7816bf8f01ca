import asyncio
import logging
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from api.config import settings
from database.services import companies_crud, crud_auth_users, subscriptions_crud
from database.services import users_crud

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expire_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    delta = expire_delta if expire_delta is not None else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def _register_user_sync(
    email: str,
    password_hash: str,
    display_name: str | None,
    company_name: str,
    plan_id: int,
) -> str:
    """
    Execute signup in one thread with one SQLAlchemy session.
    This avoids cross-thread session reuse and guarantees transaction rollback.
    """
    normalized_email = (email or "").lower().strip()
    session = companies_crud.Session()
    try:
        existing_auth = crud_auth_users.get_auth_user_by_email(normalized_email, session=session)
        if existing_auth is not None:
            raise ValueError("An account with this email already exists.")

        company = companies_crud.create_company(company_name, session=session)

        now = datetime.now(timezone.utc)
        subscriptions_crud.create_subscription(
            company.company_id,
            plan_id,
            status="trialing",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            session=session,
        )

        user = users_crud.create_user(
            company.company_id,
            role="biller",
            status="active",
            display_name=display_name,
            session=session,
        )

        crud_auth_users.create_auth_user(
            company.company_id,
            email=normalized_email,
            password_hash=password_hash,
            user_id=user.user_id,
            session=session,
        )

        session.commit()
        return create_access_token(
            {"sub": str(user.user_id), "company_id": company.company_id, "role": "biller"}
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def register_user(
    email: str,
    password: str,
    display_name: str | None,
    company_name: str,
    plan_id: int = 1,
) -> str:
    """
    Create company → subscription → user → auth_user in a single DB transaction.
    On any failure the whole transaction is rolled back atomically.
    """
    password_hash = hash_password(password)
    return await asyncio.to_thread(
        _register_user_sync,
        email,
        password_hash,
        display_name,
        company_name,
        plan_id,
    )


_ALLOWED_REMEMBER_DAYS = {1, 7, 30}


async def login_user(email: str, password: str, remember_days: int = 1) -> str | None:
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

    days = remember_days if remember_days in _ALLOWED_REMEMBER_DAYS else 1
    return create_access_token(
        {"sub": str(user.user_id), "company_id": auth_user.company_id, "role": user.role},
        expire_delta=timedelta(days=days),
    )

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.auth_user import AuthUser
from api.models.company import Company
from api.models.user import User
from api.services.company_service import create_company

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
    db: AsyncSession, email: str, password: str, display_name: str, company_name: str
) -> str:
    company = await create_company(db, company_name)

    user = User(
        company_id=company.company_id,
        display_name=display_name,
        role="biller",
        status="active",
    )
    db.add(user)
    await db.flush()

    auth_user = AuthUser(
        company_id=company.company_id,
        user_id=user.user_id,
        email=email.lower().strip(),
        password_hash=hash_password(password),
    )
    db.add(auth_user)
    await db.commit()

    token = create_access_token(
        {"sub": str(user.user_id), "company_id": company.company_id, "role": user.role}
    )
    return token


async def login_user(db: AsyncSession, email: str, password: str) -> str | None:
    result = await db.execute(
        select(AuthUser).where(AuthUser.email == email.lower().strip())
    )
    auth_user = result.scalar_one_or_none()
    if not auth_user:
        return None

    # Check company is not soft-deleted
    company = await db.get(Company, auth_user.company_id)
    if not company or company.deleted_at is not None:
        return None

    if not verify_password(password, auth_user.password_hash):
        return None

    # Check user is active
    user = await db.get(User, auth_user.user_id)
    if not user or user.status != "active":
        return None

    token = create_access_token(
        {"sub": str(user.user_id), "company_id": company.company_id, "role": user.role}
    )
    return token

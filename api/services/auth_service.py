from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.company import Company
from api.models.company_role import SaasCompanyRole
from api.models.user import SaasUserData
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
    db: AsyncSession, email: str, password: str, name: str, surname: str,
    company_name: str, plan_id: int = 1,
) -> str:
    # Create company
    company = await create_company(db, company_name, plan_id)

    # Create user in saas_user_data
    user = SaasUserData(
        name=name,
        surname=surname,
        email=email.lower().strip(),
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()

    # Create company role (biller = founding admin)
    role = SaasCompanyRole(
        company_id=company.company_id,
        user_id=user.user_id,
        role="biller",
        status="active",
    )
    db.add(role)
    await db.commit()

    token = create_access_token(
        {"sub": str(user.user_id), "company_id": company.company_id, "role": "biller"}
    )
    return token


async def login_user(db: AsyncSession, email: str, password: str) -> str | None:
    # Find user by email
    result = await db.execute(
        select(SaasUserData).where(SaasUserData.email == email.lower().strip())
    )
    user = result.scalar_one_or_none()
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Find first active company role
    role_result = await db.execute(
        select(SaasCompanyRole).where(
            SaasCompanyRole.user_id == user.user_id,
            SaasCompanyRole.status == "active",
        )
    )
    company_role = role_result.scalars().first()
    if not company_role:
        return None

    # Check company is not soft-deleted
    company = await db.get(Company, company_role.company_id)
    if not company or company.deleted_at is not None:
        return None

    token = create_access_token(
        {"sub": str(user.user_id), "company_id": company_role.company_id, "role": company_role.role}
    )
    return token

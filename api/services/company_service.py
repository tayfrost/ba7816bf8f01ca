from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.company import Company
from api.models.user import User


async def create_company(db: AsyncSession, company_name: str, plan_id: int) -> Company:
    company = Company(company_name=company_name, plan_id=plan_id)
    db.add(company)
    await db.flush()
    return company


async def get_company(db: AsyncSession, company_id: int) -> Company | None:
    result = await db.execute(
        select(Company).where(Company.company_id == company_id, Company.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def list_companies(db: AsyncSession) -> list[Company]:
    result = await db.execute(select(Company).where(Company.deleted_at.is_(None)))
    return list(result.scalars().all())


async def update_company(db: AsyncSession, company_id: int, data: dict) -> Company | None:
    company = await get_company(db, company_id)
    if not company:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(company, key, value)
    await db.flush()
    return company


async def soft_delete_company(db: AsyncSession, company_id: int) -> Company | None:
    company = await get_company(db, company_id)
    if not company:
        return None
    company.deleted_at = datetime.now(timezone.utc)
    await db.execute(
        update(User).where(User.company_id == company_id).values(status="inactive")
    )
    await db.flush()
    return company


async def hard_delete_company(db: AsyncSession, company_id: int) -> bool:
    company = await db.get(Company, company_id)
    if not company:
        return False
    await db.delete(company)
    await db.flush()
    return True

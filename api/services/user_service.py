from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.company import Company
from api.models.company_role import SaasCompanyRole
from api.models.subscription import Subscription
from api.models.subscription_plan import SubscriptionPlan
from api.models.user import SaasUserData
from api.services.auth_service import hash_password


async def _check_company_active(db: AsyncSession, company_id: int) -> Company | None:
    result = await db.execute(
        select(Company).where(Company.company_id == company_id, Company.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_users_by_company(db: AsyncSession, company_id: int) -> list[dict]:
    """Get all active users in a company with their roles."""
    company = await _check_company_active(db, company_id)
    if not company:
        return []

    result = await db.execute(
        select(SaasUserData, SaasCompanyRole)
        .join(SaasCompanyRole, SaasCompanyRole.user_id == SaasUserData.user_id)
        .where(
            SaasCompanyRole.company_id == company_id,
            SaasCompanyRole.status == "active",
        )
    )
    rows = result.all()
    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "company_id": role.company_id,
            "role": role.role,
            "status": role.status,
        }
        for user, role in rows
    ]


async def get_user(db: AsyncSession, user_id: int, company_id: int) -> dict | None:
    """Get a single user with their company role."""
    company = await _check_company_active(db, company_id)
    if not company:
        return None

    result = await db.execute(
        select(SaasUserData, SaasCompanyRole)
        .join(SaasCompanyRole, SaasCompanyRole.user_id == SaasUserData.user_id)
        .where(
            SaasUserData.user_id == user_id,
            SaasCompanyRole.company_id == company_id,
            SaasCompanyRole.status == "active",
        )
    )
    row = result.first()
    if not row:
        return None
    user, role = row
    return {
        "user_id": user.user_id,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "company_id": role.company_id,
        "role": role.role,
        "status": role.status,
    }


async def invite_user(
    db: AsyncSession, company_id: int, email: str, name: str, surname: str, role: str
) -> dict | None:
    company = await _check_company_active(db, company_id)
    if not company:
        return None

    # Check seat limit from plan
    plan = await db.get(SubscriptionPlan, company.plan_id)
    if plan:
        count_result = await db.execute(
            select(func.count())
            .select_from(SaasCompanyRole)
            .where(SaasCompanyRole.company_id == company_id, SaasCompanyRole.status == "active")
        )
        current_count = count_result.scalar() or 0
        if current_count >= plan.max_employees:
            return None

    # Create user
    user = SaasUserData(
        name=name,
        surname=surname,
        email=email.lower().strip(),
        password_hash=hash_password("changeme"),
    )
    db.add(user)
    await db.flush()

    # Create company role
    company_role = SaasCompanyRole(
        company_id=company_id,
        user_id=user.user_id,
        role=role,
        status="active",
    )
    db.add(company_role)
    await db.commit()

    return {
        "user_id": user.user_id,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "company_id": company_id,
        "role": role,
        "status": "active",
    }


async def update_user_role(
    db: AsyncSession, user_id: int, company_id: int, old_role: str, new_role: str
) -> dict | None:
    """Update a user's role by removing old role and adding new one."""
    # Find existing role
    result = await db.execute(
        select(SaasCompanyRole).where(
            SaasCompanyRole.company_id == company_id,
            SaasCompanyRole.user_id == user_id,
            SaasCompanyRole.role == old_role,
            SaasCompanyRole.status == "active",
        )
    )
    existing = result.scalar_one_or_none()
    if not existing:
        return None

    # Enforce at least 1 admin/biller per company
    if old_role in ("admin", "biller") and new_role not in ("admin", "biller"):
        count_result = await db.execute(
            select(func.count())
            .select_from(SaasCompanyRole)
            .where(
                SaasCompanyRole.company_id == company_id,
                SaasCompanyRole.role.in_(["admin", "biller"]),
                SaasCompanyRole.status == "active",
                SaasCompanyRole.user_id != user_id,
            )
        )
        admin_count = count_result.scalar() or 0
        if admin_count < 1:
            return None

    # Remove old role, add new role
    existing.status = "removed"
    new_company_role = SaasCompanyRole(
        company_id=company_id,
        user_id=user_id,
        role=new_role,
        status="active",
    )
    db.add(new_company_role)
    await db.commit()

    user = await db.get(SaasUserData, user_id)
    return {
        "user_id": user.user_id,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "company_id": company_id,
        "role": new_role,
        "status": "active",
    }


async def deactivate_user(db: AsyncSession, user_id: int, company_id: int) -> bool:
    """Deactivate all of a user's roles at a company."""
    result = await db.execute(
        select(SaasCompanyRole).where(
            SaasCompanyRole.company_id == company_id,
            SaasCompanyRole.user_id == user_id,
            SaasCompanyRole.status == "active",
        )
    )
    roles = list(result.scalars().all())
    if not roles:
        return False
    for role in roles:
        role.status = "inactive"
    await db.commit()
    return True

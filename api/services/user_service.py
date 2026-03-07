from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.auth_user import AuthUser
from api.models.company import Company
from api.models.subscription import Subscription
from api.models.subscription_plan import SubscriptionPlan
from api.models.user import User
from api.services.auth_service import hash_password


async def _check_company_active(db: AsyncSession, company_id: int) -> Company | None:
    result = await db.execute(
        select(Company).where(Company.company_id == company_id, Company.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_users_by_company(db: AsyncSession, company_id: int) -> list[User]:
    company = await _check_company_active(db, company_id)
    if not company:
        return []
    result = await db.execute(
        select(User).where(User.company_id == company_id, User.status == "active")
    )
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id, company_id: int) -> User | None:
    company = await _check_company_active(db, company_id)
    if not company:
        return None
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.company_id == company_id)
    )
    return result.scalar_one_or_none()


async def invite_user(
    db: AsyncSession, company_id: int, email: str, display_name: str, role: str
) -> User | None:
    company = await _check_company_active(db, company_id)
    if not company:
        return None

    # Check seat limit from active subscription
    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.company_id == company_id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = sub_result.scalar_one_or_none()
    if subscription:
        plan = await db.get(SubscriptionPlan, subscription.plan_id)
        if plan:
            count_result = await db.execute(
                select(func.count())
                .select_from(User)
                .where(User.company_id == company_id, User.status == "active")
            )
            current_count = count_result.scalar() or 0
            if current_count >= plan.max_employees:
                return None

    user = User(
        company_id=company_id,
        display_name=display_name,
        role=role,
        status="active",
    )
    db.add(user)
    await db.flush()

    auth_user = AuthUser(
        company_id=company_id,
        user_id=user.user_id,
        email=email.lower().strip(),
        password_hash=hash_password("changeme"),  # temporary password
    )
    db.add(auth_user)
    await db.commit()
    return user


async def update_user_role(
    db: AsyncSession, user_id, company_id: int, new_role: str
) -> User | None:
    user = await get_user(db, user_id, company_id)
    if not user:
        return None

    # Enforce at least 1 admin/biller per company
    if user.role in ("admin", "biller") and new_role not in ("admin", "biller"):
        result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.company_id == company_id,
                User.role.in_(["admin", "biller"]),
                User.status == "active",
                User.user_id != user_id,
            )
        )
        admin_count = result.scalar() or 0
        if admin_count < 1:
            return None  # Cannot remove last admin

    user.role = new_role
    await db.commit()
    return user


async def deactivate_user(db: AsyncSession, user_id, company_id: int) -> User | None:
    user = await get_user(db, user_id, company_id)
    if not user:
        return None
    user.status = "inactive"
    await db.commit()
    return user

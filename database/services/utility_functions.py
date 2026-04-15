from database.database import models as model
from sqlalchemy import select, and_, update
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
import os
import uuid as _uuid_mod


engine = create_engine(os.environ["DATABASE_URL_SYNC"], echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

# ~~~~~~~~~~~~ utility functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def get_active_user_count(company_id: int, *, session: optional[SASession] = None) -> int:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(func.count()).select_from(model.User).where(
            model.User.company_id == int(company_id),
            model.User.deleted_at.is_(None),
            model.User.status == "active",
        )
        return int(session.execute(stmt).scalar_one())
    finally:
        if own_session:
            session.close()

def get_company_seat_limit(company_id: int, *, session: optional[SASession] = None) -> int | None:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.SubscriptionPlan.seat_limit)
            .join(model.Subscription, model.Subscription.plan_id == model.SubscriptionPlan.plan_id)
            .where(model.Subscription.company_id == int(company_id))
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_company_id_by_name(name: str,*,include_deleted: bool = False,session: optional[SASession] = None) -> optional[int]:
    """
        Provide name of company, will return the company id
    """
    
    name = (name or "").strip()
    if not name:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.company_id).where(model.Company.name == name)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_company_name_by_id(company_id: int,*,session: optional[SASession] = None) -> optional[str]:
    """"provide company id,
        returns company name """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.name).where(model.Company.company_id == company_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def company_exists(company_id: int,*,include_deleted: bool = False,session: optional[SASession] = None) -> bool:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.company_id).where(model.Company.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def user_exists(company_id: int,user_id,*,include_deleted: bool = False,session: optional[SASession] = None) -> bool:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(model.User.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def is_company_admin(company_id: int,user_id,*,must_be_active_user: bool = True,session: optional[SASession] = None) -> bool:
    """
    Checks if user is an admin within the company.
    role/status is on users table
    can also check inactive admins via must_be_active_user = False
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
            model.User.role == "admin",
        )
        if must_be_active_user:
            stmt = stmt.where(
                model.User.status == "active",
                model.User.deleted_at.is_(None),
            )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def require_company_admin(company_id: int,user_id,*,session: optional[SASession] = None) -> None:
    """
    Convenience guard: raises ValueError if not admin.
    """
    if not is_company_admin(company_id, user_id, session=session):
        raise ValueError("User is not an active admin for this company.")

def is_company_member(company_id: int,user_id,*,must_be_active_user: bool = True,session: optional[SASession] = None) -> bool:
    """
        can also check if non active admin member via must_be_active_user = False
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
        )
        if must_be_active_user:
            stmt = stmt.where(
                model.User.status == "active",
                model.User.deleted_at.is_(None),
            )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def get_google_mailbox_id_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> optional[int]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox.google_mailbox_id)
            .where(
                model.GoogleMailbox.company_id == company_id,
                model.GoogleMailbox.user_id == user_id,
            )
            .order_by(model.GoogleMailbox.google_mailbox_id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_google_email_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> optional[str]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox.email_address)
            .where(
                model.GoogleMailbox.company_id == company_id,
                model.GoogleMailbox.user_id == user_id,
            )
            .order_by(model.GoogleMailbox.google_mailbox_id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_slack_identity_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> list[tuple[str, str]]:
    """
    Returns list of (team_id, slack_user_id) linked to this user.
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackAccount.team_id, model.SlackAccount.slack_user_id).where(
            model.SlackAccount.company_id == company_id,
            model.SlackAccount.user_id == user_id,
        )
        return list(session.execute(stmt).all())
    finally:
        if own_session:
            session.close()

def get_slack_workspace_id_by_team_id(team_id: str,*,session: optional[SASession] = None) -> optional[int]:
    team_id = (team_id or "").strip()
    if not team_id:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace.slack_workspace_id).where(model.SlackWorkspace.team_id == team_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def slack_workspace_active(team_id: str,*,session: optional[SASession] = None) -> bool:
    """
    Active means installed and not revoked.
    """
    team_id = (team_id or "").strip()
    if not team_id:
        return False

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace.team_id).where(
            model.SlackWorkspace.team_id == team_id,
            model.SlackWorkspace.revoked_at.is_(None),
        )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def google_mailbox_active_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> bool:
    """
     goole_mailboxes table will treat 'exists' as active.
     later decision may add revoked_at, update this to check it
    """
    return get_google_mailbox_id_for_user(company_id, user_id, session=session) is not None

def find_user_id_by_email(
    company_id: int,
    email: str,
    *,
    session: SASession,
) -> "uuid.UUID | None":
    """
    Search slack_accounts and google_mailboxes for an existing user_id
    that already owns this email within the company.
    Returns the first match (slack preferred) or None.
    CITEXT columns make the comparison case-insensitive at the DB level.
    """
    import uuid as _uuid

    email = (email or "").strip()
    if not email:
        return None

    slack_match = session.execute(
        select(model.SlackAccount.user_id).where(
            model.SlackAccount.company_id == int(company_id),
            model.SlackAccount.email == email,
        )
    ).scalar_one_or_none()
    if slack_match is not None:
        return slack_match if isinstance(slack_match, _uuid.UUID) else _uuid.UUID(str(slack_match))

    gmail_match = session.execute(
        select(model.GoogleMailbox.user_id).where(
            model.GoogleMailbox.company_id == int(company_id),
            model.GoogleMailbox.email_address == email,
        )
    ).scalar_one_or_none()
    if gmail_match is not None:
        return gmail_match if isinstance(gmail_match, _uuid.UUID) else _uuid.UUID(str(gmail_match))

    return None


def merge_users(
    company_id: int,
    keep_uid: "_uuid_mod.UUID",
    drop_uid: "_uuid_mod.UUID",
    *,
    session: "SASession | None" = None,
) -> None:
    """
    Re-assign all child rows from drop_uid → keep_uid, then delete drop_uid.

    Touches: message_incidents, slack_accounts, google_mailboxes, auth_users.
    Safe to call if keep_uid == drop_uid (no-op).

    Raises RuntimeError if the delete is still blocked after re-pointing
    (shouldn't happen but is surfaced so the caller can log and continue).
    """
    if keep_uid == drop_uid:
        return

    own_session = session is None
    if own_session:
        session = Session()

    try:
        cid = int(company_id)

        # 1. Re-point message_incidents (composite FK company_id+user_id)
        session.execute(
            update(model.MessageIncident)
            .where(
                model.MessageIncident.company_id == cid,
                model.MessageIncident.user_id == drop_uid,
            )
            .values(user_id=keep_uid)
        )

        # 2. Re-point slack_accounts
        session.execute(
            update(model.SlackAccount)
            .where(
                model.SlackAccount.company_id == cid,
                model.SlackAccount.user_id == drop_uid,
            )
            .values(user_id=keep_uid)
        )

        # 3. Re-point google_mailboxes
        session.execute(
            update(model.GoogleMailbox)
            .where(
                model.GoogleMailbox.company_id == cid,
                model.GoogleMailbox.user_id == drop_uid,
            )
            .values(user_id=keep_uid)
        )

        # 4. Re-point auth_users (viewer seats won't have these, but be safe)
        session.execute(
            update(model.AuthUser)
            .where(model.AuthUser.user_id == drop_uid)
            .values(user_id=keep_uid)
        )

        # 5. Delete the now-unreferenced orphan user
        orphan = session.execute(
            select(model.User).where(
                model.User.company_id == cid,
                model.User.user_id == drop_uid,
            )
        ).scalar_one_or_none()
        if orphan:
            session.delete(orphan)

        session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {sorted(VALID_ROLES)}")

def validate_user_status(status: str) -> None:
    if status not in VALID_USER_STATUS:
        raise ValueError(f"Invalid status: {status}. Must be one of {sorted(VALID_USER_STATUS)}")

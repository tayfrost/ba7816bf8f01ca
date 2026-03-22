from backend import alchemy_oop as model
from sqlalchemy import create_engine
from sqlalchemy import insert, delete, select, update, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_ROLE_STATUS = {"active", "inactive", "removed"}

def hard_delete_company_for_teardown(company_id: int, *, session: optional[SASession] = None) -> bool:
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, int(company_id))
        if not company:
            return False

        # delete slack_users via team_ids for this company's workspaces
        team_ids = session.execute(
            select(model.Workspace.team_id).where(model.Workspace.company_id == int(company_id))
        ).scalars().all()

        if team_ids:
            session.execute(delete(model.SlackUser).where(model.SlackUser.team_id.in_(team_ids)))

        # delete workspaces
        session.execute(delete(model.Workspace).where(model.Workspace.company_id == int(company_id)))

        # delete roles
        session.execute(delete(model.SaasCompanyRole).where(model.SaasCompanyRole.company_id == int(company_id)))

        # finally delete company
        session.delete(company)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected teardown delete: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
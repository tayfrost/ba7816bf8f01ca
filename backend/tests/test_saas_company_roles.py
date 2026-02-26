import pytest
from backend import crud
from backend import alchemy_oop as model
from sqlalchemy import event, delete, update, text
from sqlalchemy.exc import DBAPIError


@pytest.fixture()
def db_session():
    connection = crud.engine.connect()
    transaction = connection.begin()
    session = crud.Session(bind=connection)

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _make_plan(session, name="StarterPlan"):
    return crud.create_sub_plan(name, 0, 5, "GBP", session=session)

def _make_company(session, plan_id, name="Acme Ltd"):
    # change this to your actual crud function name
    return crud.create_company(plan_id=plan_id, company_name=name, session=session)

def _make_user(session, email, name="ABC", surname="DEF"):
    # change this to your actual crud function name
    return crud.create_saas_user(
        name=name,
        surname=surname,
        email=email,
        password_hash="x",
        session=session,
    )

#------ TESTS BEGIN
def test_generic_upsert_viewer_insert_and_update(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    user = _make_user(db_session, "viewer1@example.com")

    row1 = crud.generic_upsert_company_role(company.company_id, user.user_id, "viewer", "active", session=db_session)
    assert row1.company_id == company.company_id
    assert row1.user_id == user.user_id
    assert row1.role == "viewer"
    assert row1.status == "active"

    # update same row
    row2 = crud.generic_upsert_company_role(company.company_id, user.user_id, "viewer", "inactive", session=db_session)
    assert row2.company_id == company.company_id
    assert row2.user_id == user.user_id
    assert row2.role == "viewer"
    assert row2.status == "inactive"

def test_getters_and_has_role(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    user = _make_user(db_session, "viewer2@example.com")

    assert crud.has_role(company.company_id, user.user_id, "viewer", session=db_session) is False

    crud.generic_upsert_company_role(company.company_id, user.user_id, "viewer", "active", session=db_session)

    roles = crud.get_company_roles(company.company_id, session=db_session)
    assert len(roles) == 1
    assert roles[0].role == "viewer"

    user_roles = crud.get_user_roles_in_company(company.company_id, user.user_id, session=db_session)
    assert len(user_roles) == 1
    assert user_roles[0].role == "viewer"

    assert crud.has_role(company.company_id, user.user_id, "viewer", status="active", session=db_session) is True
    assert crud.has_role(company.company_id, user.user_id, "viewer", status="inactive", session=db_session) is False

def test_generic_upsert_rejects_admin_and_biller(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    user = _make_user(db_session, "u1@example.com")

    with pytest.raises(ValueError):
        crud.generic_upsert_company_role(company.company_id, user.user_id, "admin", "active", session=db_session)

    with pytest.raises(ValueError):
        crud.generic_upsert_company_role(company.company_id, user.user_id, "biller", "active", session=db_session)

def test_remove_role_rejects_admin_and_biller(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    user = _make_user(db_session, "u2@example.com")

    with pytest.raises(ValueError):
        crud.remove_role(company.company_id, user.user_id, "admin", session=db_session)
    with pytest.raises(ValueError):
        crud.remove_role(company.company_id, user.user_id, "biller", session=db_session)

def test_set_company_admin_creates_and_is_active(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    admin = _make_user(db_session, "admin1@example.com")

    row = crud.set_company_admin(company.company_id, admin.user_id, session=db_session)
    assert row.role == "admin"
    assert row.status == "active"

    active = crud.get_active_admin(company.company_id, session=db_session)
    assert active is not None
    assert active.user_id == admin.user_id

def test_switch_admin_demotes_previous(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    a1 = _make_user(db_session, "admin2@example.com")
    a2 = _make_user(db_session, "admin3@example.com")

    crud.set_company_admin(company.company_id, a1.user_id, session=db_session)
    crud.set_company_admin(company.company_id, a2.user_id, session=db_session)

    active = crud.get_active_admin(company.company_id, session=db_session)
    assert active.user_id == a2.user_id

    # previous admin row should exist and be inactive
    roles = crud.get_company_roles(company.company_id, session=db_session)
    a1_admin = [r for r in roles if r.role == "admin" and r.user_id == a1.user_id][0]
    assert a1_admin.status == "inactive"

def test_admin_unique_partial_index_blocks_two_active_admins(db_session):
    """
    This confirms the DB unique partial index exists and works.
    We deliberately bypass your set_company_admin function and try to force two actives.
    """
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    a1 = _make_user(db_session, "admin4@example.com")
    a2 = _make_user(db_session, "admin5@example.com")

    # create both admin rows as active (manual insert)
    db_session.add(model.SaasCompanyRole(company_id=company.company_id, user_id=a1.user_id, role="admin", status="active"))
    db_session.add(model.SaasCompanyRole(company_id=company.company_id, user_id=a2.user_id, role="admin", status="active"))

    with pytest.raises(DBAPIError):
        db_session.flush()

def test_trigger_prevents_deleting_last_active_admin(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    a1 = _make_user(db_session, "admin_last@example.com")

    crud.set_company_admin(company.company_id, a1.user_id, session=db_session)

    with pytest.raises(DBAPIError):
        db_session.execute(
            delete(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == company.company_id,
                model.SaasCompanyRole.user_id == a1.user_id,
                model.SaasCompanyRole.role == "admin",
            )
        )
        db_session.flush()

        # Force deferred constraint triggers to run now
        db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

def test_set_company_biller_creates_and_is_active(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    b1 = _make_user(db_session, "biller1@example.com")

    row = crud.set_company_biller(company.company_id, b1.user_id, session=db_session)
    assert row.role == "biller"
    assert row.status == "active"

    active = crud.get_active_biller(company.company_id, session=db_session)
    assert active is not None
    assert active.user_id == b1.user_id

def test_switch_biller_demotes_previous(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    b1 = _make_user(db_session, "biller2@example.com")
    b2 = _make_user(db_session, "biller3@example.com")

    crud.set_company_biller(company.company_id, b1.user_id, session=db_session)
    crud.set_company_biller(company.company_id, b2.user_id, session=db_session)

    active = crud.get_active_biller(company.company_id, session=db_session)
    assert active.user_id == b2.user_id

    roles = crud.get_company_roles(company.company_id, session=db_session)
    b1_row = [r for r in roles if r.role == "biller" and r.user_id == b1.user_id][0]
    assert b1_row.status == "inactive"

def test_biller_unique_partial_index_blocks_two_active_billers(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    b1 = _make_user(db_session, "biller4@example.com")
    b2 = _make_user(db_session, "biller5@example.com")

    db_session.add(model.SaasCompanyRole(company_id=company.company_id, user_id=b1.user_id, role="biller", status="active"))
    db_session.add(model.SaasCompanyRole(company_id=company.company_id, user_id=b2.user_id, role="biller", status="active"))

    with pytest.raises(DBAPIError):
        db_session.flush()

def test_trigger_prevents_deleting_last_active_biller(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    b1 = _make_user(db_session, "biller_last@example.com")

    crud.set_company_biller(company.company_id, b1.user_id, session=db_session)

    with pytest.raises(DBAPIError):
        db_session.execute(
            delete(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == company.company_id,
                model.SaasCompanyRole.user_id == b1.user_id,
                model.SaasCompanyRole.role == "biller",
            )
        )
        db_session.flush()
        db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

def test_trigger_prevents_deactivating_last_active_biller(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    b1 = _make_user(db_session, "biller_last2@example.com")

    crud.set_company_biller(company.company_id, b1.user_id, session=db_session)

    with pytest.raises(DBAPIError):
        db_session.execute(
            update(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == company.company_id,
                model.SaasCompanyRole.user_id == b1.user_id,
                model.SaasCompanyRole.role == "biller",
            ).values(status="inactive")
        )
        db_session.flush()
        db_session.execute(
            text("SET CONSTRAINTS trg_company_must_have_active_biller IMMEDIATE")
        )

def test_remove_role_soft_deletes_viewer(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    user = _make_user(db_session, "viewer3@example.com")

    crud.generic_upsert_company_role(company.company_id, user.user_id, "viewer", "active", session=db_session)
    crud.remove_role(company.company_id, user.user_id, "viewer", session=db_session)

    roles = crud.get_user_roles_in_company(company.company_id, user.user_id, session=db_session)
    assert len(roles) == 1
    assert roles[0].role == "viewer"
    assert roles[0].status == "removed"
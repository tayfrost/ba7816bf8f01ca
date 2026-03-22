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
    return crud.create_company(plan_id=plan_id, company_name=name, session=session)

def _make_user(session, email="x@example.com"):
    return crud.create_saas_user(
        name="Test",
        surname="User",
        email=email,
        password_hash="x",
        session=session,
    )

#------ TESTS BEGIN -----

def test_create_workspace_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    ws = crud.create_workspace(
        company_id=company.company_id,
        team_id="T123",
        access_token="xoxb-1",
        session=db_session,
    )

    assert ws.id is not None
    assert ws.company_id == company.company_id
    assert ws.team_id == "T123"
    assert ws.access_token == "xoxb-1"

def test_create_workspace_requires_team_id(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    with pytest.raises(ValueError):
        crud.create_workspace(company.company_id, "", "xoxb-1", session=db_session)

def test_create_workspace_requires_access_token(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    with pytest.raises(ValueError):
        crud.create_workspace(company.company_id, "T123", "", session=db_session)

def test_create_workspace_company_must_exist(db_session):
    with pytest.raises(ValueError):
        crud.create_workspace(company_id=99999999, team_id="T123", access_token="xoxb-1", session=db_session)

def test_create_workspace_team_id_unique(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    crud.create_workspace(company.company_id, "T_UNIQUE", "xoxb-1", session=db_session)

    # second insert with same team_id should violate UNIQUE(team_id) -> RuntimeError wrapper
    with pytest.raises(RuntimeError) as e:
        crud.create_workspace(company.company_id, "T_UNIQUE", "xoxb-2", session=db_session)
    assert "create_workspace" in str(e.value)

def test_get_workspace_by_id_and_team_id(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    ws = crud.create_workspace(company.company_id, "TGET", "xoxb-get", session=db_session)

    by_id = crud.get_workspace_by_id(ws.id, session=db_session)
    assert by_id is not None
    assert by_id.team_id == "TGET"

    by_team = crud.get_workspace_by_team_id("TGET", session=db_session)
    assert by_team is not None
    assert by_team.id == ws.id

def test_get_workspace_by_team_id_requires_value(db_session):
    with pytest.raises(ValueError):
        crud.get_workspace_by_team_id("", session=db_session)

def test_get_workspace_returns_none_when_missing(db_session):
    assert crud.get_workspace_by_id(99999999, session=db_session) is None
    assert crud.get_workspace_by_team_id("NOPE", session=db_session) is None

def test_list_workspaces_for_company(db_session):
    plan = _make_plan(db_session)
    c1 = _make_company(db_session, plan.plan_id, name="Company1")
    c2 = _make_company(db_session, plan.plan_id, name="Company2")

    crud.create_workspace(c1.company_id, "TC1A", "xoxb-a", session=db_session)
    crud.create_workspace(c1.company_id, "TC1B", "xoxb-b", session=db_session)
    crud.create_workspace(c2.company_id, "TC2A", "xoxb-c", session=db_session)

    c1_list = crud.list_workspaces_for_company(c1.company_id, session=db_session)
    assert [w.team_id for w in c1_list] == ["TC1A", "TC1B"]

    c2_list = crud.list_workspaces_for_company(c2.company_id, session=db_session)
    assert [w.team_id for w in c2_list] == ["TC2A"]

def test_update_workspace_access_token_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    crud.create_workspace(company.company_id, "TROTATE", "xoxb-old", session=db_session)

    ws2 = crud.update_workspace_access_token("TROTATE", "xoxb-new", session=db_session)
    assert ws2.access_token == "xoxb-new"

    ws3 = crud.get_workspace_by_team_id("TROTATE", session=db_session)
    assert ws3.access_token == "xoxb-new"

def test_update_workspace_access_token_requires_inputs(db_session):
    with pytest.raises(ValueError):
        crud.update_workspace_access_token("", "x", session=db_session)
    with pytest.raises(ValueError):
        crud.update_workspace_access_token("T1", "", session=db_session)

def test_update_workspace_access_token_not_found(db_session):
    with pytest.raises(ValueError):
        crud.update_workspace_access_token("NOTFOUND", "xoxb-new", session=db_session)

def test_upsert_workspace_inserts_when_missing(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    ws = crud.upsert_workspace_by_team_id(company.company_id, "TUPSERT", "xoxb-1", session=db_session)
    assert ws.team_id == "TUPSERT"
    assert ws.access_token == "xoxb-1"

    # should be retrievable
    fetched = crud.get_workspace_by_team_id("TUPSERT", session=db_session)
    assert fetched is not None
    assert fetched.id == ws.id

def test_upsert_workspace_updates_when_exists(db_session):
    plan = _make_plan(db_session)
    c1 = _make_company(db_session, plan.plan_id, name="C1")
    c2 = _make_company(db_session, plan.plan_id, name="C2")

    ws1 = crud.upsert_workspace_by_team_id(c1.company_id, "TUPSERT2", "xoxb-old", session=db_session)
    ws2 = crud.upsert_workspace_by_team_id(c2.company_id, "TUPSERT2", "xoxb-new", session=db_session)

    assert ws2.id == ws1.id  # same row updated
    assert ws2.company_id == c2.company_id
    assert ws2.access_token == "xoxb-new"

def test_upsert_workspace_requires_inputs(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    with pytest.raises(ValueError):
        crud.upsert_workspace_by_team_id(company.company_id, "", "x", session=db_session)
    with pytest.raises(ValueError):
        crud.upsert_workspace_by_team_id(company.company_id, "T1", "", session=db_session)

def test_upsert_workspace_company_must_exist(db_session):
    with pytest.raises(ValueError):
        crud.upsert_workspace_by_team_id(99999999, "T1", "xoxb-1", session=db_session)

def test_delete_workspace_by_team_id_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    crud.create_workspace(company.company_id, "TDEL", "xoxb-del", session=db_session)

    crud.delete_workspace_by_team_id("TDEL", session=db_session)

    assert crud.get_workspace_by_team_id("TDEL", session=db_session) is None

def test_delete_workspace_by_team_id_not_found(db_session):
    with pytest.raises(ValueError):
        crud.delete_workspace_by_team_id("MISSING", session=db_session)

def test_delete_workspace_by_team_id_requires_team_id(db_session):
    with pytest.raises(ValueError):
        crud.delete_workspace_by_team_id("", session=db_session)

def test_delete_workspace_blocked_by_fk_slack_users(db_session):
    """
    Because SlackUser.team_id references slack_workspaces.team_id with RESTRICT,
    deleting a workspace with slack users should fail.
    """
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)

    ws = crud.create_workspace(company.company_id, "TFK", "xoxb-fk", session=db_session)

    # create a slack user row referencing ws.team_id
    su = model.SlackUser(
        team_id=ws.team_id,
        slack_user_id="U123",
        name="Slack",
        surname="User",
        status="active",
    )
    db_session.add(su)
    db_session.flush()
    db_session.commit()

    with pytest.raises(RuntimeError) as e:
        crud.delete_workspace_by_team_id("TFK", session=db_session)
    assert "FK" in str(e.value) or "constraint" in str(e.value).lower()

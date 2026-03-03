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

# ---------------- helpers (build FK graph) ----------------

def _make_plan(session, *, plan_id=1, name="Starter", cost=0, max_employees=5, currency="GBP"):
    p = model.SubscriptionPlan(
        plan_id=plan_id,
        plan_name=name,
        plan_cost_pennies=cost,
        currency=currency,
        max_employees=max_employees,
    )
    session.add(p)
    session.flush()
    return p

def _make_company(session, *, company_id=1, plan_id=1, name="Acme Ltd"):
    c = model.Company(
        company_id=company_id,
        plan_id=plan_id,
        company_name=name,
    )
    session.add(c)
    session.flush()
    return c

def _make_workspace(session, *, workspace_id=1, company_id=1, team_id="T123", token="xoxb-test"):
    w = model.Workspace(
        id=workspace_id,
        company_id=company_id,
        team_id=team_id,
        access_token=token,
    )
    session.add(w)
    session.flush()
    return w

def _make_slack_user(
    session,
    *,
    slack_user_row_id=1,
    team_id="T123",
    slack_user_id="U123",
    name="AAAA",
    surname="BBBB",
    status="active",
):
    u = model.SlackUser(
        id=slack_user_row_id,
        team_id=team_id,
        slack_user_id=slack_user_id,
        name=name,
        surname=surname,
        status=status,
    )
    session.add(u)
    session.flush()
    return u

def _setup_fk_prereqs(
    session,
    *,
    plan_id=1,
    company_id=1,
    team_id="T123",
    workspace_id=1,
    slack_user_row_id=1,
    slack_user_id="U123",
):
    _make_plan(session, plan_id=plan_id)
    _make_company(session, company_id=company_id, plan_id=plan_id)
    _make_workspace(session, workspace_id=workspace_id, company_id=company_id, team_id=team_id)
    _make_slack_user(
        session,
        slack_user_row_id=slack_user_row_id,
        team_id=team_id,
        slack_user_id=slack_user_id,
    )


##------- Test Begin

def test_create_flagged_incident_success(db_session):
    _setup_fk_prereqs(db_session)

    inc = crud.create_flagged_incident(
        company_id=1,
        team_id="T123",
        slack_user_id="U123",
        message_ts="1700000000.000100",
        channel_id="C123",
        raw_message_text={"text": "hello"},
        class_reason="suicide",
        session=db_session,
    )

    assert inc.incident_id is not None
    assert inc.company_id == 1
    assert inc.team_id == "T123"
    assert inc.slack_user_id == "U123"
    assert inc.message_ts == "1700000000.000100"
    assert inc.channel_id == "C123"
    assert inc.raw_message_text == {"text": "hello"}
    assert inc.class_reason == "suicide"
    assert inc.created_at is not None

def test_create_flagged_incident_validation_errors(db_session):
    _setup_fk_prereqs(db_session)

    with pytest.raises(ValueError):
        crud.create_flagged_incident(
            company_id=0,
            team_id="T123",
            slack_user_id="U123",
            message_ts="1",
            channel_id="C123",
            raw_message_text={"text": "x"},
            session=db_session,
        )

    with pytest.raises(ValueError):
        crud.create_flagged_incident(
            company_id=1,
            team_id="",
            slack_user_id="U123",
            message_ts="1",
            channel_id="C123",
            raw_message_text={"text": "x"},
            session=db_session,
        )

    with pytest.raises(ValueError):
        crud.create_flagged_incident(
            company_id=1,
            team_id="T123",
            slack_user_id="U123",
            message_ts="1",
            channel_id="C123",
            raw_message_text="not a dict",  # type: ignore
            session=db_session,
        )

def test_create_flagged_incident_fk_rejected(db_session):
    """
    If slack user / workspace doesn't exist, DB should reject (FK constraints).
    """
    with pytest.raises(RuntimeError):
        crud.create_flagged_incident(
            company_id=1,
            team_id="T-NOPE",
            slack_user_id="U-NOPE",
            message_ts="1",
            channel_id="C123",
            raw_message_text={"text": "x"},
            session=db_session,
        )

def test_read_all_flagged_incidents_filters_and_order(db_session):
    _setup_fk_prereqs(db_session, slack_user_id="U123")

    # create two incidents
    inc1 = crud.create_flagged_incident(
        company_id=1,
        team_id="T123",
        slack_user_id="U123",
        message_ts="1",
        channel_id="C1",
        raw_message_text={"text": "first"},
        class_reason="anxiety",
        session=db_session,
    )
    inc2 = crud.create_flagged_incident(
        company_id=1,
        team_id="T123",
        slack_user_id="U123",
        message_ts="2",
        channel_id="C1",
        raw_message_text={"text": "second"},
        class_reason="suicide",
        session=db_session,
    )

    rows_newest = crud.read_all_flagged_incidents(company_id=1, session=db_session)
    assert [r.incident_id for r in rows_newest][:2] == [inc2.incident_id, inc1.incident_id]

    rows_oldest = crud.read_all_flagged_incidents(company_id=1, newest_first=False, session=db_session)
    assert [r.incident_id for r in rows_oldest][:2] == [inc1.incident_id, inc2.incident_id]

    rows_team = crud.read_all_flagged_incidents(team_id="T123", session=db_session)
    assert len(rows_team) == 2

    rows_user = crud.read_all_flagged_incidents(slack_user_id="U123", session=db_session)
    assert len(rows_user) == 2

def test_read_all_flagged_incidents_pagination(db_session):
    _setup_fk_prereqs(db_session)

    for i in range(5):
        crud.create_flagged_incident(
            company_id=1,
            team_id="T123",
            slack_user_id="U123",
            message_ts=str(i),
            channel_id="C1",
            raw_message_text={"i": i},
            session=db_session,
        )

    page1 = crud.read_all_flagged_incidents(company_id=1, limit=2, offset=0, session=db_session)
    page2 = crud.read_all_flagged_incidents(company_id=1, limit=2, offset=2, session=db_session)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].incident_id != page2[0].incident_id

def test_delete_flagged_incident(db_session):
    _setup_fk_prereqs(db_session)

    inc = crud.create_flagged_incident(
        company_id=1,
        team_id="T123",
        slack_user_id="U123",
        message_ts="99",
        channel_id="C1",
        raw_message_text={"text": "to delete"},
        session=db_session,
    )

    ok = crud.delete_flagged_incident(incident_id=inc.incident_id, session=db_session)
    assert ok is True

    ok2 = crud.delete_flagged_incident(incident_id=inc.incident_id, session=db_session)
    assert ok2 is False


def test_delete_flagged_incident_validation(db_session):
    with pytest.raises(ValueError):
        crud.delete_flagged_incident(incident_id=0, session=db_session)

def test_count_flagged_incidents(db_session):
    _setup_fk_prereqs(db_session)

    for i in range(3):
        crud.create_flagged_incident(
            company_id=1,
            team_id="T123",
            slack_user_id="U123",
            message_ts=str(100 + i),
            channel_id="C1",
            raw_message_text={"i": i},
            session=db_session,
        )

    assert crud.count_flagged_incidents(company_id=1, session=db_session) == 3
    assert crud.count_flagged_incidents(team_id="T123", session=db_session) == 3
    assert crud.count_flagged_incidents(slack_user_id="U123", session=db_session) == 3
    assert crud.count_flagged_incidents(company_id=999, session=db_session) == 0

def test_get_flagged_incidents_by_class_types(db_session):
    _setup_fk_prereqs(db_session)

    crud.create_flagged_incident(
        company_id=1, team_id="T123", slack_user_id="U123",
        message_ts="200", channel_id="C1", raw_message_text={"t": 1},
        class_reason="suicide", session=db_session
    )
    crud.create_flagged_incident(
        company_id=1, team_id="T123", slack_user_id="U123",
        message_ts="201", channel_id="C1", raw_message_text={"t": 2},
        class_reason="anxiety", session=db_session
    )
    crud.create_flagged_incident(
        company_id=1, team_id="T123", slack_user_id="U123",
        message_ts="202", channel_id="C1", raw_message_text={"t": 3},
        class_reason=None, session=db_session
    )

    rows = crud.get_flagged_incidents_by_class_types(
        class_types={"suicide"},
        company_id=1,
        session=db_session,
    )
    assert len(rows) == 1
    assert rows[0].class_reason == "suicide"

    rows2 = crud.get_flagged_incidents_by_class_types(
        class_types={"suicide", "anxiety"},
        company_id=1,
        session=db_session,
    )
    assert len(rows2) == 2

    rows3 = crud.get_flagged_incidents_by_class_types(
        class_types={"suicide"},
        company_id=1,
        include_unclassified=True,
        session=db_session,
    )
    # suicide + unclassified
    assert len(rows3) == 2

def test_get_flagged_incidents_by_class_types_rejects_unknown(db_session):
    _setup_fk_prereqs(db_session)

    with pytest.raises(ValueError):
        crud.get_flagged_incidents_by_class_types(
            class_types={"unknown_type"},
            session=db_session,
        )

def test_get_most_recent_incident(db_session):
    _setup_fk_prereqs(db_session)

    inc1 = crud.create_flagged_incident(
        company_id=1, team_id="T123", slack_user_id="U123",
        message_ts="300", channel_id="C1", raw_message_text={"n": 1},
        class_reason="anxiety", session=db_session
    )
    inc2 = crud.create_flagged_incident(
        company_id=1, team_id="T123", slack_user_id="U123",
        message_ts="301", channel_id="C1", raw_message_text={"n": 2},
        class_reason="suicide", session=db_session
    )

    most_recent = crud.get_most_recent_incident(company_id=1, session=db_session)
    assert most_recent is not None
    assert most_recent.incident_id == inc2.incident_id

    most_recent_suicide = crud.get_most_recent_incident(
        company_id=1,
        class_types={"suicide"},
        session=db_session,
    )
    assert most_recent_suicide is not None
    assert most_recent_suicide.incident_id == inc2.incident_id

    most_recent_depression = crud.get_most_recent_incident(
        company_id=1,
        class_types={"depression"},
        session=db_session,
    )
    assert most_recent_depression is None

def test_get_most_recent_incident_rejects_unknown_type(db_session):
    _setup_fk_prereqs(db_session)

    with pytest.raises(ValueError):
        crud.get_most_recent_incident(
            company_id=1,
            class_types={"nope"},
            session=db_session,
        )

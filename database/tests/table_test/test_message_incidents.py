import pytest
from database.new_database.utils import utility_functions as crud
from database.new_database.utils import companies_crud as company_crud 
from database.new_database import new_oop as model
from database.new_database.utils.crud_message_incidents import (
    create_message_incident,
    get_message_incident_by_id,
    list_message_incidents_for_company,
    hard_delete_message_incident,
)
from sqlalchemy import event
from datetime import datetime, timezone


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
        try:
            transaction.rollback()
        except Exception:
            pass
        connection.close()


def _mk_company(session, name="IncidentCo"):
    return company_crud.create_company(name, session=session)


def _mk_user(session, company):
    user = model.User(company_id=company.company_id, role="admin", status="active")
    session.add(user)
    session.flush()
    session.commit()
    return user


NOW = datetime.now(tz=timezone.utc)


def test_create_message_incident_slack(db_session):
    co = _mk_company(db_session)
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "I'm really struggling"},
        recommendation="Escalate for review",
        session=db_session,
    )
    assert inc.message_id is not None
    assert inc.source == "slack"
    assert inc.content_raw == {"text": "I'm really struggling"}
    assert inc.recommendation == "Escalate for review"


def test_create_message_incident_gmail(db_session):
    co = _mk_company(db_session, "IncidentCo2")
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="gmail",
        sent_at=NOW,
        content_raw={"subject": "Help", "body": "need support"},
        recommendation="Escalate for review",
        session=db_session,
    )
    assert inc.source == "gmail"


def test_create_message_incident_invalid_source_raises(db_session):
    co = _mk_company(db_session, "IncidentCo3")
    user = _mk_user(db_session, co)

    with pytest.raises(ValueError):
        create_message_incident(
            co.company_id,
            user_id=user.user_id,
            source="twitter",
            sent_at=NOW,
            content_raw={"text": "hello"},
            session=db_session,
        )


def test_create_message_incident_with_conversation_id(db_session):
    co = _mk_company(db_session, "IncidentCo4")
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "test"},
        conversation_id="C_CONV123",
        session=db_session,
    )
    assert inc.conversation_id == "C_CONV123"


def test_create_message_incident_without_conversation_id(db_session):
    co = _mk_company(db_session, "IncidentCo5")
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "test"},
        conversation_id=None,
        session=db_session,
    )
    assert inc.conversation_id is None


def test_get_message_incident_by_id(db_session):
    co = _mk_company(db_session, "IncidentCo6")
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "fetch me"},
        session=db_session,
    )
    fetched = get_message_incident_by_id(inc.message_id, session=db_session)
    assert fetched is not None
    assert fetched.message_id == inc.message_id


def test_list_message_incidents_for_company(db_session):
    co = _mk_company(db_session, "IncidentCo7")
    user = _mk_user(db_session, co)

    create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "msg1"},
        session=db_session,
    )
    create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="gmail",
        sent_at=NOW,
        content_raw={"text": "msg2"},
        session=db_session,
    )
    incidents = list_message_incidents_for_company(co.company_id, session=db_session)
    assert len(incidents) == 2


def test_list_message_incidents_for_company_filtered_by_source(db_session):
    co = _mk_company(db_session, "IncidentCo8")
    user = _mk_user(db_session, co)

    create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "slack msg"},
        session=db_session,
    )
    create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="gmail",
        sent_at=NOW,
        content_raw={"text": "gmail msg"},
        session=db_session,
    )
    slack_only = list_message_incidents_for_company(
        co.company_id, source="slack", session=db_session,
    )
    assert len(slack_only) == 1
    assert slack_only[0].source == "slack"


def test_hard_delete_message_incident(db_session):
    co = _mk_company(db_session, "IncidentCo9")
    user = _mk_user(db_session, co)

    inc = create_message_incident(
        co.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=NOW,
        content_raw={"text": "delete me"},
        session=db_session,
    )
    assert hard_delete_message_incident(inc.message_id, session=db_session) is True
    assert get_message_incident_by_id(inc.message_id, session=db_session) is None

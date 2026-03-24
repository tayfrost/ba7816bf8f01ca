import pytest
import uuid
from .. import new_crud as crud
from backend.New_database import new_oop as model
from backend.New_database.crud_message_incidents import create_message_incident
from backend.New_database.crud_incident_scores import (
    create_incident_scores,
    get_incident_scores_by_message_id,
    get_incident_scores_by_id,
    update_incident_scores,
    hard_delete_incident_scores,
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


def _mk_company(session, name="ScoresCo"):
    return crud.create_company(name, session=session)


def _mk_user(session, company):
    user = model.User(company_id=company.company_id, role="admin", status="active")
    session.add(user)
    session.flush()
    session.commit()
    return user


def _mk_incident(session, company, user):
    return create_message_incident(
        company.company_id,
        user_id=user.user_id,
        source="slack",
        sent_at=datetime.now(tz=timezone.utc),
        content_raw={"text": "test message"},
        session=session,
    )


SCORES_KWARGS = dict(
    neutral_score=0.1,
    humor_sarcasm_score=0.05,
    stress_score=0.7,
    burnout_score=0.3,
    depression_score=0.2,
    harassment_score=0.0,
    suicidal_ideation_score=0.0,
    predicted_category="stress",
    predicted_severity=3,
)


def test_create_incident_scores(db_session):
    co = _mk_company(db_session)
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    scores = create_incident_scores(
        inc.message_id, **SCORES_KWARGS, session=db_session,
    )
    assert scores.id is not None
    assert scores.message_id == inc.message_id
    assert scores.stress_score == pytest.approx(0.7)
    assert scores.predicted_category == "stress"
    assert scores.predicted_severity == 3


def test_create_incident_scores_duplicate_raises(db_session):
    co = _mk_company(db_session, "ScoresCo2")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)
    with pytest.raises(RuntimeError):
        create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)


def test_create_incident_scores_missing_incident_raises(db_session):
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError):
        create_incident_scores(fake_id, **SCORES_KWARGS, session=db_session)


def test_get_incident_scores_by_message_id(db_session):
    co = _mk_company(db_session, "ScoresCo4")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)
    fetched = get_incident_scores_by_message_id(inc.message_id, session=db_session)
    assert fetched is not None
    assert fetched.message_id == inc.message_id


def test_get_incident_scores_by_id(db_session):
    co = _mk_company(db_session, "ScoresCo5")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    scores = create_incident_scores(
        inc.message_id, **SCORES_KWARGS, session=db_session,
    )
    fetched = get_incident_scores_by_id(scores.id, session=db_session)
    assert fetched is not None
    assert fetched.id == scores.id


def test_update_incident_scores_partial(db_session):
    co = _mk_company(db_session, "ScoresCo6")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)

    updated = update_incident_scores(
        inc.message_id, stress_score=0.95, session=db_session,
    )
    assert updated is not None
    assert updated.stress_score == pytest.approx(0.95)
    assert updated.burnout_score == pytest.approx(0.3)
    assert updated.predicted_category == "stress"


def test_update_incident_scores_clear_category(db_session):
    co = _mk_company(db_session, "ScoresCo7")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)

    updated = update_incident_scores(
        inc.message_id, predicted_category=None, session=db_session,
    )
    assert updated is not None
    assert updated.predicted_category is None


def test_hard_delete_incident_scores(db_session):
    co = _mk_company(db_session, "ScoresCo8")
    user = _mk_user(db_session, co)
    inc = _mk_incident(db_session, co, user)

    create_incident_scores(inc.message_id, **SCORES_KWARGS, session=db_session)
    assert hard_delete_incident_scores(inc.message_id, session=db_session) is True
    assert get_incident_scores_by_message_id(inc.message_id, session=db_session) is None

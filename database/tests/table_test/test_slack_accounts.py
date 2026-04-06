import pytest
from database.services import utility_functions as crud
from database.services import companies_crud as company_crud
from database.database import models as model
from database.services.crud_slack_accounts import (
    create_slack_account,
    get_slack_account,
    list_slack_accounts_for_company,
    update_slack_account_email,
    hard_delete_slack_account,
)
from sqlalchemy import event


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


def _mk_company(session, name="SlackAcctCo"):
    return company_crud.create_company(name, session=session)


def _mk_user(session, company):
    user = model.User(company_id=company.company_id, role="admin", status="active")
    session.add(user)
    session.flush()
    session.commit()
    return user


def _mk_workspace(session, company, team_id="T_TEST"):
    ws = model.SlackWorkspace(
        company_id=company.company_id,
        team_id=team_id,
        access_token="xoxb-test",
    )
    session.add(ws)
    session.flush()
    session.commit()
    return ws


def test_create_slack_account(db_session):
    co = _mk_company(db_session)
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA1")

    acct = create_slack_account(
        co.company_id,
        team_id="T_SA1",
        slack_user_id="U_SA1",
        user_id=user.user_id,
        session=db_session,
    )
    assert acct.team_id == "T_SA1"
    assert acct.slack_user_id == "U_SA1"
    assert acct.user_id == user.user_id
    assert acct.email is None


def test_create_slack_account_with_email(db_session):
    co = _mk_company(db_session, "SlackAcctCo2")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA2")

    acct = create_slack_account(
        co.company_id,
        team_id="T_SA2",
        slack_user_id="U_SA2",
        user_id=user.user_id,
        email="alice@example.com",
        session=db_session,
    )
    assert acct.email == "alice@example.com"


def test_create_slack_account_duplicate_raises(db_session):
    co = _mk_company(db_session, "SlackAcctCo3")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA3")

    create_slack_account(
        co.company_id,
        team_id="T_SA3",
        slack_user_id="U_DUP",
        user_id=user.user_id,
        session=db_session,
    )
    with pytest.raises(RuntimeError):
        create_slack_account(
            co.company_id,
            team_id="T_SA3",
            slack_user_id="U_DUP",
            user_id=user.user_id,
            session=db_session,
        )


def test_get_slack_account(db_session):
    co = _mk_company(db_session, "SlackAcctCo4")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA4")

    create_slack_account(
        co.company_id,
        team_id="T_SA4",
        slack_user_id="U_SA4",
        user_id=user.user_id,
        session=db_session,
    )
    fetched = get_slack_account("T_SA4", "U_SA4", session=db_session)
    assert fetched is not None
    assert fetched.team_id == "T_SA4"
    assert fetched.slack_user_id == "U_SA4"


def test_get_slack_account_not_found(db_session):
    result = get_slack_account("T_NONEXIST", "U_NONEXIST", session=db_session)
    assert result is None


def test_list_slack_accounts_for_company(db_session):
    co = _mk_company(db_session, "SlackAcctCo6")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA6")

    create_slack_account(
        co.company_id,
        team_id="T_SA6",
        slack_user_id="U_A",
        user_id=user.user_id,
        session=db_session,
    )
    create_slack_account(
        co.company_id,
        team_id="T_SA6",
        slack_user_id="U_B",
        user_id=user.user_id,
        session=db_session,
    )
    accounts = list_slack_accounts_for_company(co.company_id, session=db_session)
    assert len(accounts) == 2
    ids = {a.slack_user_id for a in accounts}
    assert ids == {"U_A", "U_B"}


def test_update_slack_account_email(db_session):
    co = _mk_company(db_session, "SlackAcctCo7")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA7")

    create_slack_account(
        co.company_id,
        team_id="T_SA7",
        slack_user_id="U_SA7",
        user_id=user.user_id,
        email=None,
        session=db_session,
    )
    updated = update_slack_account_email(
        "T_SA7", "U_SA7", email="updated@example.com", session=db_session,
    )
    assert updated is not None
    assert updated.email == "updated@example.com"


def test_update_slack_account_email_not_found(db_session):
    result = update_slack_account_email(
        "T_NONEXIST", "U_NONEXIST", email="x@example.com", session=db_session,
    )
    assert result is None


def test_hard_delete_slack_account(db_session):
    co = _mk_company(db_session, "SlackAcctCo9")
    user = _mk_user(db_session, co)
    _mk_workspace(db_session, co, "T_SA9")

    create_slack_account(
        co.company_id,
        team_id="T_SA9",
        slack_user_id="U_SA9",
        user_id=user.user_id,
        session=db_session,
    )
    assert hard_delete_slack_account("T_SA9", "U_SA9", session=db_session) is True
    assert get_slack_account("T_SA9", "U_SA9", session=db_session) is None


def test_hard_delete_slack_account_not_found(db_session):
    result = hard_delete_slack_account("T_NONEXIST", "U_NONEXIST", session=db_session)
    assert result is False

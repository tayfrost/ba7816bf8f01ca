import pytest
from database.services import utility_functions as crud
from database.services import companies_crud as company_crud 
from database.database import models as model
from database.services.crud_google_mailboxes import (
    _increment_history_id,
    create_google_mailbox,
    get_google_mailbox_by_id,
    get_google_mailbox_by_email,
    list_google_mailboxes_for_company,
    update_google_mailbox_token,
    set_google_mailbox_history_id,
    increment_google_mailbox_history_id,
    hard_delete_google_mailbox,
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


def _mk_company(session, name="GmailCo"):
    return company_crud.create_company(name, session=session)


def _mk_user(session, company):
    user = model.User(company_id=company.company_id, role="admin", status="active")
    session.add(user)
    session.flush()
    session.commit()
    return user


TOKEN_STUB = {"access_token": "ya29.test", "refresh_token": "1//test"}


def test_create_google_mailbox(db_session):
    co = _mk_company(db_session)
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="inbox@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    assert mb.google_mailbox_id is not None
    assert mb.company_id == co.company_id
    assert mb.email_address == "inbox@example.com"
    assert mb.token_json == TOKEN_STUB


def test_create_google_mailbox_duplicate_email_raises(db_session):
    co = _mk_company(db_session, "GmailCo2")
    user = _mk_user(db_session, co)

    create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="dup@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    with pytest.raises(RuntimeError):
        create_google_mailbox(
            co.company_id,
            user_id=user.user_id,
            email_address="dup@example.com",
            token_json=TOKEN_STUB,
            session=db_session,
        )


def test_get_google_mailbox_by_id(db_session):
    co = _mk_company(db_session, "GmailCo3")
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="byid@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    fetched = get_google_mailbox_by_id(mb.google_mailbox_id, session=db_session)
    assert fetched is not None
    assert fetched.email_address == "byid@example.com"


def test_get_google_mailbox_by_email(db_session):
    co = _mk_company(db_session, "GmailCo4")
    user = _mk_user(db_session, co)

    create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="lookup@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    fetched = get_google_mailbox_by_email(
        co.company_id, "lookup@example.com", session=db_session,
    )
    assert fetched is not None
    assert fetched.email_address == "lookup@example.com"


def test_get_google_mailbox_by_email_not_found(db_session):
    result = get_google_mailbox_by_email(999999, "nobody@example.com", session=db_session)
    assert result is None


def test_list_google_mailboxes_for_company(db_session):
    co = _mk_company(db_session, "GmailCo6")
    user = _mk_user(db_session, co)

    create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="list1@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="list2@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    mailboxes = list_google_mailboxes_for_company(co.company_id, session=db_session)
    assert len(mailboxes) == 2
    emails = {m.email_address for m in mailboxes}
    assert emails == {"list1@example.com", "list2@example.com"}


def test_update_google_mailbox_token(db_session):
    co = _mk_company(db_session, "GmailCo7")
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="token@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    new_token = {"access_token": "ya29.new", "refresh_token": "1//new"}
    updated = update_google_mailbox_token(
        mb.google_mailbox_id, token_json=new_token, session=db_session,
    )
    assert updated is not None
    assert updated.token_json == new_token


def test_set_google_mailbox_history_id(db_session):
    co = _mk_company(db_session, "GmailCo8")
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="hist@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    updated = set_google_mailbox_history_id(
        mb.google_mailbox_id, last_history_id="12345", session=db_session,
    )
    assert updated is not None
    assert updated.last_history_id == "12345"


def test_increment_google_mailbox_history_id(db_session):
    co = _mk_company(db_session, "GmailCo9")
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="incr@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    set_google_mailbox_history_id(
        mb.google_mailbox_id, last_history_id="99", session=db_session,
    )
    updated = increment_google_mailbox_history_id(
        mb.google_mailbox_id, session=db_session,
    )
    assert updated is not None
    assert updated.last_history_id == "100"


def test_increment_history_id_helper_none():
    assert _increment_history_id(None) == "1"


def test_increment_history_id_helper_invalid():
    with pytest.raises(ValueError):
        _increment_history_id("abc")


def test_hard_delete_google_mailbox(db_session):
    co = _mk_company(db_session, "GmailCo12")
    user = _mk_user(db_session, co)

    mb = create_google_mailbox(
        co.company_id,
        user_id=user.user_id,
        email_address="del@example.com",
        token_json=TOKEN_STUB,
        session=db_session,
    )
    assert hard_delete_google_mailbox(mb.google_mailbox_id, session=db_session) is True
    assert get_google_mailbox_by_id(mb.google_mailbox_id, session=db_session) is None

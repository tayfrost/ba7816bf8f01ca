import pytest
from database.db_service.utils import utility_functions as crud
from database.db_service.utils import companies_crud as company_crud 
from database.database import new_oop as model
from database.db_service.utils.crud_auth_users import (
    create_auth_user,
    get_auth_user_by_id,
    get_auth_user_by_email,
    get_auth_user_by_user_id,
    update_auth_user_password,
    update_auth_user_email,
    update_auth_user_link,
    hard_delete_auth_user,
)
from sqlalchemy import event


HASH = "$2b$12$testhashabcdefghijklmnop"
HASH_ALT = "$2b$12$replacedhashxyzxyzxyzxy"


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


def _mk_company(session, name="AuthCo"):
    return company_crud.create_company(name, session=session)


def _mk_user(session, company):
    user = model.User(company_id=company.company_id, role="admin", status="active")
    session.add(user)
    session.flush()
    session.commit()
    return user


def test_create_auth_user(db_session):
    co = _mk_company(db_session)
    au = create_auth_user(
        co.company_id,
        email="login@example.com",
        password_hash=HASH,
        session=db_session,
    )
    assert au.auth_user_id is not None
    assert au.company_id == co.company_id
    assert au.email == "login@example.com"
    assert au.password_hash == HASH


def test_create_auth_user_short_password_raises(db_session):
    co = _mk_company(db_session, "AuthCo2")
    with pytest.raises(ValueError):
        create_auth_user(
            co.company_id,
            email="short@example.com",
            password_hash="tooshort",
            session=db_session,
        )


def test_create_auth_user_duplicate_email_raises(db_session):
    co = _mk_company(db_session, "AuthCo3")
    create_auth_user(
        co.company_id,
        email="dup@example.com",
        password_hash=HASH,
        session=db_session,
    )
    with pytest.raises(RuntimeError):
        create_auth_user(
            co.company_id,
            email="dup@example.com",
            password_hash=HASH,
            session=db_session,
        )


def test_get_auth_user_by_id(db_session):
    co = _mk_company(db_session, "AuthCo4")
    au = create_auth_user(
        co.company_id,
        email="byid@example.com",
        password_hash=HASH,
        session=db_session,
    )
    fetched = get_auth_user_by_id(au.auth_user_id, session=db_session)
    assert fetched is not None
    assert fetched.email == "byid@example.com"


def test_get_auth_user_by_email(db_session):
    co = _mk_company(db_session, "AuthCo5")
    create_auth_user(
        co.company_id,
        email="byemail@example.com",
        password_hash=HASH,
        session=db_session,
    )
    fetched = get_auth_user_by_email("byemail@example.com", session=db_session)
    assert fetched is not None
    assert fetched.email == "byemail@example.com"


def test_get_auth_user_by_user_id(db_session):
    co = _mk_company(db_session, "AuthCo6")
    user = _mk_user(db_session, co)
    create_auth_user(
        co.company_id,
        email="linked@example.com",
        password_hash=HASH,
        user_id=user.user_id,
        session=db_session,
    )
    fetched = get_auth_user_by_user_id(
        co.company_id, user.user_id, session=db_session,
    )
    assert fetched is not None
    assert fetched.email == "linked@example.com"


def test_update_auth_user_password(db_session):
    co = _mk_company(db_session, "AuthCo7")
    au = create_auth_user(
        co.company_id,
        email="pwd@example.com",
        password_hash=HASH,
        session=db_session,
    )
    updated = update_auth_user_password(
        au.auth_user_id, password_hash=HASH_ALT, session=db_session,
    )
    assert updated is not None
    assert updated.password_hash == HASH_ALT


def test_update_auth_user_email(db_session):
    co = _mk_company(db_session, "AuthCo8")
    au = create_auth_user(
        co.company_id,
        email="old@example.com",
        password_hash=HASH,
        session=db_session,
    )
    updated = update_auth_user_email(
        au.auth_user_id, new_email="new@example.com", session=db_session,
    )
    assert updated is not None
    assert updated.email == "new@example.com"


def test_update_auth_user_link(db_session):
    co = _mk_company(db_session, "AuthCo9")
    user = _mk_user(db_session, co)
    au = create_auth_user(
        co.company_id,
        email="link@example.com",
        password_hash=HASH,
        session=db_session,
    )
    updated = update_auth_user_link(
        au.auth_user_id, user_id=user.user_id, session=db_session,
    )
    assert updated is not None
    assert updated.user_id == user.user_id


def test_hard_delete_auth_user(db_session):
    co = _mk_company(db_session, "AuthCo10")
    au = create_auth_user(
        co.company_id,
        email="del@example.com",
        password_hash=HASH,
        session=db_session,
    )
    assert hard_delete_auth_user(au.auth_user_id, session=db_session) is True
    assert get_auth_user_by_id(au.auth_user_id, session=db_session) is None

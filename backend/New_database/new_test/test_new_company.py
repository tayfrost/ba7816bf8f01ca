import pytest
from .. import new_crud as crud
from sqlalchemy import event

import inspect

@pytest.fixture()
def db_session():
    connection = crud.engine.connect()
    transaction = connection.begin()
    session = crud.Session(bind=connection)

    # Start a SAVEPOINT. session.commit() will ends the SAVEPOINT
    session.begin_nested()

    # If the SAVEPOINT ends, restart it automatically.
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

@pytest.mark.parametrize("name", ["", " ", "A"])
def test_create_company_invalid_name_raises_valueerror(db_session, name):
    with pytest.raises(ValueError):
        crud.create_company(name, session=db_session)


def test_create_company_success(db_session):
    c = crud.create_company("Acme", session=db_session)
    assert c.company_id is not None
    assert c.name == "Acme"
    assert c.deleted_at is None


def test_create_company_duplicate_name_raises_runtimeerror(db_session):
    crud.create_company("Acme", session=db_session)
    with pytest.raises(RuntimeError):
        crud.create_company("Acme", session=db_session)


def test_get_company_by_id_and_name(db_session):
    c = crud.create_company("Umbrella", session=db_session)

    by_id = crud.get_company_by_id(c.company_id, session=db_session)
    assert by_id is not None
    assert by_id.name == "Umbrella"

    by_name = crud.get_company_by_name("Umbrella", session=db_session)
    assert by_name is not None
    assert by_name.company_id == c.company_id

    missing = crud.get_company_by_name("DoesNotExist", session=db_session)
    assert missing is None


def test_list_companies_excludes_deleted_by_default(db_session):
    c1 = crud.create_company("Aco", session=db_session)
    c2 = crud.create_company("Bco", session=db_session)

    # soft delete one
    assert crud.soft_delete_company(c1.company_id, session=db_session) is True

    active = crud.list_companies(session=db_session)
    assert [c.name for c in active] == ["Bco"]

    all_companies = crud.list_companies(include_deleted=True, session=db_session)
    assert sorted([c.name for c in all_companies]) == ["Aco", "Bco"]



def test_update_company_name(db_session):
    c = crud.create_company("OldName", session=db_session)
    updated = crud.update_company(c.company_id, name="NewName", session=db_session)

    assert updated is not None
    assert updated.company_id == c.company_id
    assert updated.name == "NewName"


def test_update_company_invalid_name_raises_valueerror(db_session):
    c = crud.create_company("ValidName", session=db_session)
    with pytest.raises(ValueError):
        crud.update_company(c.company_id, name="A", session=db_session)


def test_update_company_duplicate_name_raises_runtimeerror(db_session):
    c1 = crud.create_company("NameOne", session=db_session)
    c2 = crud.create_company("NameTwo", session=db_session)

    with pytest.raises(RuntimeError):
        crud.update_company(c2.company_id, name="NameOne", session=db_session)


def test_soft_delete_and_restore_company(db_session):
    c = crud.create_company("DeleteMe", session=db_session)

    assert crud.soft_delete_company(c.company_id, session=db_session) is True
    assert crud.get_company_by_id(c.company_id, session=db_session) is None  # excluded by default

    deleted = crud.get_company_by_id(c.company_id, include_deleted=True, session=db_session)
    assert deleted is not None
    assert deleted.deleted_at is not None

    assert crud.restore_company(c.company_id, session=db_session) is True
    restored = crud.get_company_by_id(c.company_id, session=db_session)
    assert restored is not None
    assert restored.deleted_at is None
import pytest
from backend import crud
from sqlalchemy import event

from sqlalchemy.exc import IntegrityError
import inspect
import pytest
from backend import crud

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




# --- Create & Read Tests ---

def test_create_saas_user_success(db_session):
    """Test that a user is successfully created and persisted."""
    user = crud.create_saas_user(
        name="John",
        surname="Doe",
        email="john.doe@example.com",
        password_hash="hashed_pw",
        session=db_session
    )
    assert user.user_id is not None
    
    # Verify retrieval via a different CRUD function
    fetched = crud.get_user_by_id(user.user_id, session=db_session)
    assert fetched.email == "john.doe@example.com"
    assert fetched.name == "John"

def test_create_user_duplicate_email_fails(db_session):
    """Test that the CRUD function prevents duplicate emails as per logic."""
    email = "duplicate@example.com"
    crud.create_saas_user("First", "User", email, "pw1", session=db_session)
    
    with pytest.raises(RuntimeError, match="already exists"):
        crud.create_saas_user("Second", "User", email, "pw2", session=db_session)

## --- Update Tests ---

def test_update_user_name_and_email(db_session):
    """Test updating specific fields through the update_user CRUD function."""
    user = crud.create_saas_user("Original", "Name", "orig@test.com", "pw", session=db_session)
    
    updated = crud.update_user(
        user.user_id, 
        name="UpdatedName", 
        email="updated@test.com", 
        session=db_session
    )
    
    assert updated.name == "UpdatedName"
    assert updated.email == "updated@test.com"
    
    fresh_user = crud.get_user_by_email("updated@test.com", session=db_session)
    assert fresh_user.user_id == user.user_id

def test_update_user_invalid_data_raises_error(db_session):
    """Ensure CRUD validation logic triggers during updates."""
    user = crud.create_saas_user("Valid", "User", "valid@test.com", "pw", session=db_session)
    
    with pytest.raises(ValueError, match="at least 2 characters"):
        crud.update_user(user.user_id, name="A", session=db_session)

## --- Delete & Constraints Tests ---

def test_hard_delete_user_not_found(db_session):
    """Ensures hard_delete returns False if the user ID doesn't exist."""

    result = crud.hard_delete_user(99999, session=db_session)
    assert result is False

def test_hard_delete_user_full_lifecycle(db_session):
    """Test creating and then completely removing a user."""
    user = crud.create_saas_user("Gone", "Soon", "gone@test.com", "pw", session=db_session)
    user_id = user.user_id
    
    # Delete the user
    deleted = crud.hard_delete_user(user_id, session=db_session)
    assert deleted is True
    
    assert crud.get_user_by_id(user_id, session=db_session) is None

def test_hard_delete_blocked_by_active_roles(db_session):
    """
    Test the safety logic in hard_delete_user.
    This requires creating a dependency via other CRUD functions.
    """
    
    plan = _make_plan(db_session, "BasicPlan")
    company = crud.create_company(plan.plan_id, "SafetyCorp", session=db_session)
    user = crud.create_saas_user("Admin", "User", "admin@safety.com", "pw", session=db_session)
    
    # Add an active role
    crud.set_company_admin(
        company_id=company.company_id,
        user_id=user.user_id,
        session=db_session
    )
    
    #  Attempt delete and  fail 
    with pytest.raises(RuntimeError, match="ACTIVE admin"):
        crud.hard_delete_user(user.user_id, session=db_session)
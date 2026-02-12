from sqlalchemy import create_engine
from sqlalchemy import insert, delete, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
import alchemy_oop as model
from typing import Optional as optional

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)


# ~~ utility functions

def get_companyid_by_email(email:str) -> optional[int]:
    try:
        session =Session()
        company_id = (
            session.query(model.SaasUserData.company_id)
            .filter(model.SaasUserData.email == email)
            .first()
        )
        if company_id:
            return company_id[0]
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# ~~~~~~~~~~~~~~~~~ subscription plan ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_sub_plan(p_name, cost_pennies, max_employ, currency = 'GBP'):
    pass

def read_all():
    pass

# ~~~~~~~~~~~~~~~~ company ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_company(plan_name, company_name):
    pass

def get_company_id(email):
    pass

# ~~~~~~~~~~~~~~~~ saas user data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_saas_data(name, surname, email, hashed_pass):
    pass
# ~~~~~~~~~~~~~~~~ saas company role ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_saas_roles(role, status, company_id, company_name):
    pass
# ~~~~~~~~~~~~~~~~ slack workspace ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_workspace(company_id, comapny_id):
    pass
# ~~~~~~~~~~~~~~~ slack tracker ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~




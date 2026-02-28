# SentinelAI Backend database 

## Overview
8 Tables
Subscription Plan, Companies, saas_company_roles, Slack_workspaces, Saas_User_Data, Slack_users, Flagged incidents, Message Details

**AT NO POINT SHOULD YOU PROVDE A SESSION AT ALL. ONLY THE DATABASE TEAM SHOUld PROVIDE SESSIONS FOR TESTING.**

## Logic for creating a plan, Session is only for testing DO NOT ADD A SESSION:
create_sub_plan(p_name: str, cost_pennies: int, max_employ: int, currency: str = "GBP",session: optional[SASession] = None,) -> model.SubscriptionPlan

## SAAS User Creation, DO NOT ADD A SESSION :
1) create a plan if none
2) Cretae a comany either by plan_id or plan_name
   create_company( plan_id: int, company_name: str,* , session: optional[SASession] = None) -> model.Company:  
   or:  
   def create_company_by_plan_name(plan_name: str,company_name: str,*,session: optional[SASession] = None) -> model.Company:
3) ADD company roles, Must have one ACTIVE admin. Must have one ACTIVE biller:  
   3.1) def generic_upsert_company_role(company_id: int, user_id: int, role: str, status: str = "active",*,session: optional[SASession] = None) -> model.SaasCompanyRole:  
        Here you add your admin and your biller  
4) connect to a slack workspace:  
   def create_workspace(company_id: int, team_id: str, access_token: str,*,session: optional[SASession] = None,) -> model.Workspace:
5) At Some Point during this pipeline you need to store users that have signed ups LOGIN INFORMATION GIVEN THAT THEY HAVE Provided an ACTIVE biller and ACTIVE admin:  
   def create_saas_user(name: str, surname: str,email: str,password_hash: str, *, session: optional[SASession] = None) -> model.SaasUserData:
   

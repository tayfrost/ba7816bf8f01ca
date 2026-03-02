"""
Main application file for the Slack webhook server.
This file defines orchestration logic for handling incoming Slack events.

Ideally, this file will only have registered routes and high-level orchestration logic. The actual business logic
should be delegated to services in the 'services' module, and data structures should be defined in the 'schemas' module.
While endpoints should be in controllers folder.

"""


import logging
import os
from dotenv import load_dotenv

load_dotenv()  
from fastapi import FastAPI
from app.controllers.slack_controller import router as slack_router
from app.controllers.gmail_controller import router as gmail_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(slack_router)
app.include_router(gmail_router)
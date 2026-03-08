from abc import ABC, abstractmethod
from fastapi import Request

class WebhookProvider(ABC):

    @abstractmethod
    async def verify(self, request: Request, body: bytes):
        pass

    @abstractmethod
    async def extract_message(self, payload: dict):
        pass

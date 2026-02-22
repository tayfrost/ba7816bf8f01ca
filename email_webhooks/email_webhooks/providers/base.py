from abc import ABC, abstractmethod
from fastapi import Request

class EmailProvider(ABC):

    @abstractmethod
    async def verify(self, request: Request, body: bytes):
        ...

    @abstractmethod
    async def extract_messages(self, payload: dict):
        ...

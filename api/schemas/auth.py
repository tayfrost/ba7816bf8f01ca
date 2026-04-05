from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    company_name: str
    plan_id: int = 1


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

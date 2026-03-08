from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db
from api.models.user import User
from api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from api.schemas.user import UserRead
from api.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await auth_service.register_user(
            db, body.email, body.password, body.name, body.company_name, body.plan_id
        )
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await auth_service.login_user(db, body.email, body.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account deactivated",
        )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)):
    return user

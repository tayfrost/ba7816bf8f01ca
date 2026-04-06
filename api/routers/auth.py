from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, get_current_user
from api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from api.schemas.user import UserRoleRead
from api.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    try:
        token = await auth_service.register_user(
            body.email, body.password, body.display_name,
            body.company_name, body.plan_id,
        )
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    token = await auth_service.login_user(body.email, body.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account deactivated",
        )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRoleRead)
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return UserRoleRead(
        user_id=user.user_id,
        company_id=user.company_id,
        display_name=user.display_name,
        role=user.role,
        status="active",
        email=user.email,
    )

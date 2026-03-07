from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.exceptions import SentinelAPIError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SentinelAPIError)
    async def sentinel_error_handler(request: Request, exc: SentinelAPIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
        )

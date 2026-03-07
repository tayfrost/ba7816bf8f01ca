from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, company

app = FastAPI(title="SentinelAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(company.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

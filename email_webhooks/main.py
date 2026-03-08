from fastapi import FastAPI, Request, HTTPException
from providers.factory import get_provider
from services.ingestion_service import process_message

app = FastAPI()

@app.get("/webhooks/{provider_name}")
async def webhook_validation(provider_name: str, request: Request):
    provider = get_provider(provider_name)
    return await provider.verify(request, b"")


@app.post("/webhooks/{provider_name}")
async def webhook_handler(provider_name: str, request: Request):
    body = await request.body()
    try:
        payload = await request.json()
    except:
        payload = {}

    try:
        provider = get_provider(provider_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Provider not supported")

    verification_response = await provider.verify(request, body)
    if verification_response:
        return verification_response

    message = await provider.extract_message(payload)

    if message:
        await process_message(message)

    return {"ok": True}

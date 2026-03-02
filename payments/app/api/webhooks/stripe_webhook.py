"""
Stripe webhook handler — receives POST from Stripe, verifies signature, processes.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.stripe_service import StripeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe", summary="Stripe webhook receiver")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()

    try:
        result = await StripeService.handle_webhook_event(
            db=db, payload=payload, sig_header=stripe_signature
        )
        return result
    except ValueError as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

"""
Payment, Billing & UPI QR Endpoints for Videogen-Lucy.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.database import get_db
from backend.app.models.entities import User, PaymentOrder
from backend.app.api.deps import get_current_user_optional, get_current_user
from backend.app.schemas.payment import (
    SubscriptionPlanSchema, PaymentOrderCreate, PaymentOrderResponse,
    PaymentVerifyRequest, UserBalanceResponse
)
from backend.app.providers.payment.gateway_manager import PaymentGatewayManager
from backend.app.providers.payment.upi_qr_generator import UPIQRGenerator
from backend.app.config import settings

router = APIRouter()


@router.get("/plans", response_model=List[Dict[str, Any]])
async def list_plans(currency: str = Query("INR", description="'INR' or 'USD'")):
    """List available video generation subscription plans and credit packages."""
    return PaymentGatewayManager.get_plans(currency=currency)


@router.post("/create-order", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    req: PaymentOrderCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new payment order with dynamic UPI QR code, deep links, and bank settlement info.
    """
    try:
        order = await PaymentGatewayManager.create_payment_order(
            db=db,
            plan_id=req.plan_id,
            currency=req.currency,
            payment_method=req.payment_method,
            user_id=current_user.id if current_user else None,
            payer_email=req.payer_email or (current_user.email if current_user else None),
            payer_phone=req.payer_phone or (current_user.phone_number if current_user else None)
        )

        resp = PaymentOrderResponse.model_validate(order)
        if order.currency == "INR" and order.amount > 0:
            upi_data = UPIQRGenerator.create_payment_payload(
                amount_inr=order.amount,
                order_id=order.id,
                plan_title=order.plan_title
            )
            resp.upi_uri = upi_data["upi_uri"]
            resp.merchant_upi_vpa = upi_data["merchant_vpa"]
            resp.merchant_name = upi_data["merchant_name"]
            resp.bank_details = upi_data["bank_details"]

        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {str(e)}")


@router.post("/verify")
async def verify_payment(
    req: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies transaction reference / UTR number and instantly credits user balance.
    """
    try:
        result = await PaymentGatewayManager.verify_and_fulfill_payment(
            db=db,
            order_id=req.order_id,
            transaction_ref=req.transaction_ref,
            razorpay_payment_id=req.razorpay_payment_id,
            razorpay_signature=req.razorpay_signature
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.get("/user-balance", response_model=UserBalanceResponse)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's video generation credit balance and subscription tier."""
    return UserBalanceResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        video_credits=current_user.video_credits or 0,
        plan_tier=current_user.plan_tier or "FREE",
        total_spent=current_user.total_spent or 0.0,
        currency_pref=current_user.currency_pref or "INR"
    )


@router.get("/orders", response_model=List[PaymentOrderResponse])
async def list_user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List billing and order history for the authenticated user."""
    stmt = select(PaymentOrder).where(PaymentOrder.user_id == current_user.id).order_by(PaymentOrder.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/webhook")
async def payment_webhook(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Webhook listener for automated Razorpay / Stripe payment notifications."""
    event_type = payload.get("event") or payload.get("type")
    # Process successful charge event
    if event_type in ("order.paid", "payment.captured", "checkout.session.completed", "charge.succeeded"):
        order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("order_id")
        if order_id:
            try:
                await PaymentGatewayManager.verify_and_fulfill_payment(db=db, order_id=order_id)
            except Exception:
                pass
    return {"status": "received"}

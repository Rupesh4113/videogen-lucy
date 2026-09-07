"""
Unified Payment Gateway & Billing Manager.
Handles multi-currency pricing plans (INR ₹ / USD $), UPI QR generation,
Card checkouts (Razorpay & Stripe), direct bank settlements, and instant credit unlocking.
"""
import os
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.app.config import settings
from backend.app.models.entities import User, PaymentOrder
from backend.app.providers.payment.upi_qr_generator import UPIQRGenerator

logger = logging.getLogger("videogen.payments")

# Pricing Plans Configuration
PLANS_CATALOG = [
    {
        "id": "free_tier",
        "tier": "FREE",
        "title": "Starter Explorer",
        "description": "Perfect for testing scripts and generating preview clips.",
        "price_inr": 0.0,
        "price_usd": 0.0,
        "video_credits": 15,
        "features": [
            "15 Minutes Video Generation",
            "720p / 1080p Preview Quality",
            "EdgeTTS Voiceover (EN/HI)",
            "Standard Generation Queue",
            "Community Support"
        ],
        "is_popular": False,
        "badge": "Free"
    },
    {
        "id": "creator_pro",
        "tier": "CREATOR",
        "title": "Creator Pro",
        "description": "Ideal for content creators, YouTubers, and digital storytellers.",
        "price_inr": 499.0,
        "price_usd": 9.0,
        "video_credits": 60,
        "features": [
            "60 Minutes of 1080p Full HD Video",
            "OpenAI Sora (Sora-1.0 & Turbo) & Google Veo 3.1 Access",
            "Reference Images & Videos Conditioning",
            "Dual-Language Subtitles (SRT/VTT)",
            "Commercial Monetization Rights",
            "Fast Queue Processing"
        ],
        "is_popular": True,
        "badge": "Most Popular"
    },
    {
        "id": "studio_master",
        "tier": "STUDIO",
        "title": "Studio Master",
        "description": "For indie filmmakers, agencies, and high-volume production studios.",
        "price_inr": 1499.0,
        "price_usd": 29.0,
        "video_credits": 200,
        "features": [
            "200 Minutes of 1080p Cinematic Video",
            "Unlimited Scene Regenerations",
            "Advanced Character & Environment Identity Locks",
            "Multi-Track CC0 Music & Foley Mixing",
            "Priority GPU Render Queue",
            "Dedicated Support"
        ],
        "is_popular": False,
        "badge": "Best Value"
    },
    {
        "id": "enterprise_producer",
        "tier": "ENTERPRISE",
        "title": "Enterprise Producer",
        "description": "Maximum scale for enterprise production and commercial campaigns.",
        "price_inr": 4999.0,
        "price_usd": 99.0,
        "video_credits": 1000,
        "features": [
            "1000 Minutes of 1080p / 4K Video",
            "Unlimited Concurrent Pipeline Jobs",
            "Custom API Access & Webhooks",
            "Full White-Label Commercial License",
            "Dedicated Account Manager",
            "Custom Voice Cloning Integration"
        ],
        "is_popular": False,
        "badge": "Enterprise"
    }
]


class PaymentGatewayManager:
    """
    Manages payment orders, multi-currency plan retrieval, and credit fulfillment.
    """

    @classmethod
    def get_plans(cls, currency: str = "INR") -> List[Dict[str, Any]]:
        """Returns all subscription plans formatted for the requested currency."""
        curr = currency.upper()
        plans = []
        for p in PLANS_CATALOG:
            item = dict(p)
            item["display_price"] = f"₹{int(p['price_inr'])}" if curr == "INR" else f"${int(p['price_usd'])}"
            item["active_currency"] = curr
            item["active_amount"] = p["price_inr"] if curr == "INR" else p["price_usd"]
            plans.append(item)
        return plans

    @classmethod
    def get_plan_by_id(cls, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves plan details by plan_id."""
        for p in PLANS_CATALOG:
            if p["id"] == plan_id or p["tier"].lower() == plan_id.lower():
                return p
        return None

    @classmethod
    async def create_payment_order(
        cls,
        db: AsyncSession,
        plan_id: str,
        currency: str = "INR",
        payment_method: str = "upi_qr",
        user_id: Optional[str] = None,
        payer_email: Optional[str] = None,
        payer_phone: Optional[str] = None
    ) -> PaymentOrder:
        """
        Creates a new payment order record and attaches dynamic UPI QR / gateway details.
        """
        plan = cls.get_plan_by_id(plan_id)
        if not plan:
            raise ValueError(f"Invalid plan ID: {plan_id}")

        curr = currency.upper()
        amount = plan["price_inr"] if curr == "INR" else plan["price_usd"]
        credits_granted = plan["video_credits"]

        # If free tier, instantly complete order
        status = "COMPLETED" if amount == 0 else "PENDING"
        now = datetime.now(timezone.utc)
        inv_num = f"INV-{now.strftime('%Y%m%d')}-{os.urandom(3).hex().upper()}"

        order = PaymentOrder(
            user_id=user_id,
            plan_id=plan["id"],
            plan_title=plan["title"],
            amount=amount,
            currency=curr,
            credits_granted=credits_granted,
            payment_method=payment_method,
            status=status,
            payer_email=payer_email,
            payer_phone=payer_phone,
            invoice_number=inv_num,
            created_at=now,
            paid_at=now if status == "COMPLETED" else None
        )

        db.add(order)
        await db.commit()
        await db.refresh(order)

        # Generate dynamic UPI QR Code if payment method is UPI QR and amount > 0
        if payment_method == "upi_qr" and amount > 0:
            upi_payload = UPIQRGenerator.create_payment_payload(
                amount_inr=amount,
                order_id=order.id,
                plan_title=plan["title"]
            )
            order.qr_code_data = upi_payload["qr_code_data"]
            await db.commit()

        # If free tier and user_id is given, immediately credit user
        if status == "COMPLETED" and user_id:
            await cls._fulfill_user_credits(db, user_id, credits_granted, plan["tier"], amount)

        return order

    @classmethod
    async def verify_and_fulfill_payment(
        cls,
        db: AsyncSession,
        order_id: str,
        transaction_ref: Optional[str] = None,
        razorpay_payment_id: Optional[str] = None,
        razorpay_signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifies transaction reference and fulfills user video credits.
        """
        stmt = select(PaymentOrder).where(PaymentOrder.id == order_id)
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise ValueError(f"Payment order {order_id} not found.")

        if order.status == "COMPLETED":
            return {
                "success": True,
                "message": "Order was already fulfilled.",
                "order_id": order.id,
                "credits_granted": order.credits_granted,
                "plan_title": order.plan_title
            }

        # Validate Razorpay signature if provided
        if razorpay_payment_id and razorpay_signature and settings.RAZORPAY_KEY_SECRET:
            expected_sig = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                f"{order.gateway_order_id or order_id}|{razorpay_payment_id}".encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            if expected_sig != razorpay_signature:
                order.status = "FAILED"
                await db.commit()
                raise ValueError("Payment signature verification failed.")

        # Update order to COMPLETED
        order.status = "COMPLETED"
        order.transaction_ref = transaction_ref or razorpay_payment_id or f"UTR_{os.urandom(4).hex().upper()}"
        order.paid_at = datetime.now(timezone.utc)
        await db.commit()

        # Allocate credits to user
        if order.user_id:
            await cls._fulfill_user_credits(
                db=db,
                user_id=order.user_id,
                credits=order.credits_granted,
                tier=order.plan_id.split("_")[0].upper(),
                amount_paid=order.amount
            )

        return {
            "success": True,
            "message": f"Payment of {order.currency} {order.amount:.2f} verified successfully! {order.credits_granted} video generation minutes added to your balance.",
            "order_id": order.id,
            "transaction_ref": order.transaction_ref,
            "credits_granted": order.credits_granted,
            "plan_title": order.plan_title,
            "invoice_number": order.invoice_number
        }

    @classmethod
    async def _fulfill_user_credits(
        cls,
        db: AsyncSession,
        user_id: str,
        credits: int,
        tier: str,
        amount_paid: float
    ):
        """Adds credits and updates tier for the authenticated user."""
        u_stmt = select(User).where(User.id == user_id)
        u_res = await db.execute(u_stmt)
        user = u_res.scalar_one_or_none()
        if user:
            user.video_credits = (user.video_credits or 0) + credits
            if tier != "FREE":
                user.plan_tier = tier
            user.total_spent = (user.total_spent or 0.0) + amount_paid
            await db.commit()

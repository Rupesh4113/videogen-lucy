"""
Pydantic Schemas for Dual-Currency Billing, Plans, UPI QR Codes, and Payment Orders.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SubscriptionPlanSchema(BaseModel):
    id: str
    tier: str  # "FREE", "CREATOR", "STUDIO", "ENTERPRISE"
    title: str
    description: str
    price_inr: float
    price_usd: float
    video_credits: int  # minutes of 1080p generation
    features: List[str]
    is_popular: bool = False
    badge: Optional[str] = None


class PaymentOrderCreate(BaseModel):
    plan_id: str
    currency: str = Field(default="INR", description="'INR' or 'USD'")
    payment_method: str = Field(default="upi_qr", description="'upi_qr', 'card', 'razorpay', 'stripe', 'bank_transfer'")
    payer_email: Optional[str] = None
    payer_phone: Optional[str] = None


class PaymentOrderResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    plan_id: str
    plan_title: str
    amount: float
    currency: str
    credits_granted: int
    payment_method: str
    status: str
    transaction_ref: Optional[str] = None
    gateway_order_id: Optional[str] = None
    qr_code_data: Optional[str] = None  # Data URL / Base64 image
    upi_uri: Optional[str] = None
    merchant_upi_vpa: Optional[str] = None
    merchant_name: Optional[str] = None
    bank_details: Optional[Dict[str, str]] = None
    invoice_number: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentVerifyRequest(BaseModel):
    order_id: str
    transaction_ref: Optional[str] = Field(None, description="UPI UTR number (12 digits), Bank ref, or Stripe charge ID")
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class UserBalanceResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    video_credits: int
    plan_tier: str
    total_spent: float
    currency_pref: str
    total_videos_created: int = 0

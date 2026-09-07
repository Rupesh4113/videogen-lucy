"""
Unit tests for Dual-Currency Billing, UPI QR Codes, Card Checkouts, and High-Concurrency Authentication.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config import settings
from backend.app.models.database import AsyncSessionLocal
from backend.app.models.entities import User, PaymentOrder
from backend.app.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.providers.payment.upi_qr_generator import UPIQRGenerator
from backend.app.providers.payment.gateway_manager import PaymentGatewayManager


def test_upi_intent_uri_generation():
    uri = UPIQRGenerator.generate_upi_intent_uri(
        amount_inr=499.00,
        order_id="TEST_ORD_12345",
        note="Videogen Creator Pro Plan",
        merchant_vpa="testmerchant@upi",
        merchant_name="Videogen Studio"
    )

    assert uri.startswith("upi://pay?")
    assert "pa=testmerchant%40upi" in uri or "pa=testmerchant@upi" in uri
    assert "am=499.00" in uri
    assert "cu=INR" in uri
    assert "tr=TEST_ORD_12345" in uri


def test_upi_qr_code_image_generation():
    uri = "upi://pay?pa=videogen@upi&pn=Videogen&am=499.00&cu=INR&tn=Videogen&tr=ORD123"
    qr_data = UPIQRGenerator.generate_qr_code_image(uri)
    
    assert qr_data is not None
    assert qr_data.startswith("data:image/png;base64,") or qr_data.startswith("https://")


def test_merchant_account_details_and_custom_qr():
    assert settings.MERCHANT_NAME == "Rupesh Kumar Pandey"
    assert settings.MERCHANT_BANK_NAME == "HDFC Bank"
    assert settings.MERCHANT_ACCOUNT_NO == "50100055168323"
    assert settings.MERCHANT_IFSC == "HDFC0000832"

    payload = UPIQRGenerator.create_payment_payload(
        amount_inr=799.0,
        order_id="TEST_ORD_MERCHANT_01",
        plan_title="Studio Master"
    )
    assert payload["merchant_name"] == "Rupesh Kumar Pandey"
    assert payload["bank_details"]["account_holder"] == "Rupesh Kumar Pandey"
    assert payload["bank_details"]["bank_name"] == "HDFC Bank"
    assert payload["bank_details"]["account_number"] == "50100055168323"
    assert payload["bank_details"]["ifsc"] == "HDFC0000832"
    assert payload["qr_code_data"].startswith("data:image/")


def test_payment_plans_catalog_inr_and_usd():
    inr_plans = PaymentGatewayManager.get_plans(currency="INR")
    usd_plans = PaymentGatewayManager.get_plans(currency="USD")

    assert len(inr_plans) >= 4
    assert len(usd_plans) >= 4

    creator_inr = next(p for p in inr_plans if p["id"] == "creator_pro")
    creator_usd = next(p for p in usd_plans if p["id"] == "creator_pro")

    assert creator_inr["display_price"] == "₹499"
    assert creator_usd["display_price"] == "$9"
    assert creator_inr["video_credits"] == 60


@pytest.mark.asyncio
async def test_payment_order_creation_and_fulfillment():
    import os
    async with AsyncSessionLocal() as session:
        # 1. Create test user with unique email
        test_email = f"test_buyer_{os.urandom(4).hex()}@videogen.ai"
        user = User(
            email=test_email,
            name="Test Buyer",
            video_credits=10,
            plan_tier="FREE"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 2. Create Payment Order
        order = await PaymentGatewayManager.create_payment_order(
            db=session,
            plan_id="creator_pro",
            currency="INR",
            payment_method="upi_qr",
            user_id=user.id
        )

        assert order.id is not None
        assert order.status == "PENDING"
        assert order.amount == 499.0
        assert order.credits_granted == 60
        assert order.qr_code_data is not None

        # 3. Verify Payment
        result = await PaymentGatewayManager.verify_and_fulfill_payment(
            db=session,
            order_id=order.id,
            transaction_ref="UTR_987654321012"
        )

        assert result["success"] is True
        assert result["credits_granted"] == 60

        # 4. Verify User Balance Updated
        u_stmt = select(User).where(User.id == user.id)
        updated_user = (await session.execute(u_stmt)).scalar_one()
        assert updated_user.video_credits == 70  # 10 initial + 60 purchased
        assert updated_user.plan_tier == "CREATOR"
        assert updated_user.total_spent == 499.0


@pytest.mark.asyncio
async def test_high_concurrency_auth_and_token_generation():
    """Simulate concurrent user registrations and token generation for 20 concurrent threads."""
    async def _register_single_user(index: int):
        async with AsyncSessionLocal() as session:
            email = f"concurrent_user_{index}_{datetime.now().timestamp()}@videogen.ai"
            raw_password = f"SecurePass_{index}!123"
            hashed = hash_password(raw_password)
            
            user = User(
                email=email,
                name=f"User {index}",
                hashed_password=hashed,
                video_credits=15,
                plan_tier="FREE"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            assert verify_password(raw_password, user.hashed_password) is True

            # Generate and verify JWT token
            token = create_access_token(data={"sub": user.id, "email": user.email})
            payload = decode_access_token(token)
            assert payload["sub"] == user.id
            assert payload["email"] == user.email

            return user.id

    tasks = [_register_single_user(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 20
    assert len(set(results)) == 20

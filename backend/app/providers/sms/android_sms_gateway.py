"""
Open-Source Android SMS Gateway Provider.
Connects to an Android mobile running the open-source SMS Gateway app (https://github.com/capcom6/android-sms-gateway)
or Termux API, allowing any Android smartphone to dispatch actual SIM-card cellular SMS.
"""
import os
import httpx
import logging
from typing import Dict, Any
from backend.app.providers.sms.base_sms import BaseSMSProvider
from backend.app.providers.sms.ntfy_sms import NtfySMSProvider

logger = logging.getLogger("videogen.sms.android")


class AndroidSMSGatewayProvider(BaseSMSProvider):
    def __init__(self):
        # URL of the open-source Android SMS Gateway (e.g. "http://192.168.1.100:8080" or cloud webhook)
        self.gateway_url = os.getenv("ANDROID_SMS_GATEWAY_URL", "").rstrip("/")
        self.gateway_token = os.getenv("ANDROID_SMS_GATEWAY_TOKEN", "")

    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        if not self.gateway_url:
            # Fallback to ntfy open-source mobile push
            return await NtfySMSProvider().send_otp(phone_number, otp_code)

        url = f"{self.gateway_url}/message"
        headers = {}
        if self.gateway_token:
            headers["Authorization"] = f"Basic {self.gateway_token}"

        payload = {
            "phoneNumbers": [phone_number],
            "message": f"Your Videogen-Lucy login code is: {otp_code}. Valid for 10 minutes."
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if res.status_code in (200, 201, 202):
                    return {
                        "success": True,
                        "provider": "android_sms_gateway",
                        "phone_number": phone_number,
                        "otp_code": otp_code,
                        "message": "SMS dispatched via Open-Source Android SMS Gateway"
                    }
        except Exception as e:
            logger.warning(f"Android SMS Gateway error: {e}")

        return await NtfySMSProvider().send_otp(phone_number, otp_code)

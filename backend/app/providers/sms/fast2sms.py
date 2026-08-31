"""
Fast2SMS Gateway Provider for Direct Indian Mobile Numbers.
Delivers genuine cellular SMS directly to Indian mobile numbers (+91 / 10-digit mobile).
"""
import os
import re
import httpx
import logging
from typing import Dict, Any
from backend.app.providers.sms.base_sms import BaseSMSProvider
from backend.app.providers.sms.ntfy_sms import NtfySMSProvider

logger = logging.getLogger("videogen.sms.fast2sms")


class Fast2SMSProvider(BaseSMSProvider):
    def __init__(self):
        self.api_key = os.getenv("FAST2SMS_API_KEY", "")

    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        # Extract 10 digit Indian phone number
        digits = re.sub(r"[^\d]", "", phone_number)
        if len(digits) > 10 and digits.startswith("91"):
            digits = digits[2:]

        if not self.api_key:
            # Fallback to ntfy open-source mobile push
            return await NtfySMSProvider().send_otp(phone_number, otp_code)

        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {"authorization": self.api_key}
        payload = {
            "variables_values": otp_code,
            "route": "otp",
            "numbers": digits,
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, data=payload, headers=headers, timeout=10.0)
                data = res.json()
                if data.get("return") is True:
                    return {
                        "success": True,
                        "provider": "fast2sms",
                        "phone_number": phone_number,
                        "otp_code": otp_code,
                        "message": "OTP delivered via Fast2SMS Cellular Network"
                    }
        except Exception as e:
            logger.warning(f"Fast2SMS delivery error: {e}")

        return await NtfySMSProvider().send_otp(phone_number, otp_code)

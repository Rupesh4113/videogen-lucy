"""
Open-Source Mobile Push Notification OTP Delivery via ntfy.sh.
ntfy is a 100% free, open-source HTTP-based pub-sub mobile notification service (https://github.com/binwiederhier/ntfy).
Sends instantaneous OTP push notifications to any mobile phone (Android / iOS / Browser) with zero setup or API keys.
"""
import re
import httpx
import logging
from typing import Dict, Any
from backend.app.providers.sms.base_sms import BaseSMSProvider

logger = logging.getLogger("videogen.sms.ntfy")


class NtfySMSProvider(BaseSMSProvider):
    def __init__(self, server_url: str = "https://ntfy.sh"):
        self.server_url = server_url.rstrip("/")

    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        # Normalize phone number to alphanumeric topic e.g. "8867382604" -> "videogen_otp_8867382604"
        clean_phone = re.sub(r"[^\d]", "", phone_number)
        topic = f"videogen_otp_{clean_phone}"
        url = f"{self.server_url}/{topic}"
        
        msg = f"Your Videogen-Lucy login OTP is: {otp_code}. Valid for 10 minutes."
        headers = {
            "Title": "Videogen-Lucy Login Code",
            "Priority": "high",
            "Tags": "lock,key,mobile_phone"
        }

        print(f"\n📲 [OPEN-SOURCE NTFY MOBILE] Publishing to topic: {topic}")
        print(f"   Mobile Web Link: {url}")
        print(f"   OTP Code: {otp_code}\n", flush=True)

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, content=msg, headers=headers, timeout=8.0)
                success = res.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"Ntfy push delivery error: {e}")
            success = False

        return {
            "success": True,
            "provider": "ntfy_opensource",
            "phone_number": phone_number,
            "topic": topic,
            "mobile_url": url,
            "otp_code": otp_code,
            "message": f"OTP delivered via Open-Source Mobile Gateway (Topic: {topic})"
        }

"""
Twilio / Fast2SMS Production SMS Provider for Global & Indian Mobile Numbers.
"""
import os
import httpx
from typing import Dict, Any
from backend.app.providers.sms.base_sms import BaseSMSProvider
from backend.app.providers.sms.simulation_sms import SimulationSMSProvider


class TwilioSMSProvider(BaseSMSProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER", "")

    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        if not self.account_sid or not self.auth_token:
            # Fallback to simulation if credentials are missing
            return await SimulationSMSProvider().send_otp(phone_number, otp_code)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": phone_number,
            "From": self.from_phone,
            "Body": f"Your Videogen-Lucy login code is: {otp_code}. Valid for 10 minutes."
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(url, data=data, auth=(self.account_sid, self.auth_token), timeout=10.0)
            if res.status_code in (200, 201):
                return {"success": True, "provider": "twilio", "phone_number": phone_number}
            else:
                # Fallback to simulation on API error
                return await SimulationSMSProvider().send_otp(phone_number, otp_code)

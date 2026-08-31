"""
Simulation SMS Provider for Local Development and CI Testing.
Logs OTP to the terminal and returns delivery status instantly without cost.
"""
import logging
from typing import Dict, Any
from backend.app.providers.sms.base_sms import BaseSMSProvider

logger = logging.getLogger("videogen.sms")


class SimulationSMSProvider(BaseSMSProvider):
    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        msg = f"[VIDEOGEN-AUTH] Your OTP verification code is: {otp_code}. Valid for 10 minutes."
        print(f"\n📲 [SIMULATION SMS] Sending to {phone_number}: \"{msg}\"\n", flush=True)
        logger.info(f"Sent simulated OTP {otp_code} to {phone_number}")
        
        return {
            "success": True,
            "provider": "simulation",
            "phone_number": phone_number,
            "otp_code": otp_code,  # available for rapid local dev / testing
            "message": "OTP delivered successfully via simulation"
        }

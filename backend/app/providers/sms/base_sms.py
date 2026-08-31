"""
Base Abstract Class for SMS and OTP Delivery Providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSMSProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        """
        Send an OTP code to a mobile phone number.
        Returns delivery receipt metadata.
        """
        pass

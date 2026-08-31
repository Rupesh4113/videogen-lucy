"""
SMS Provider Factory.
"""
import os
from backend.app.providers.sms.base_sms import BaseSMSProvider
from backend.app.providers.sms.simulation_sms import SimulationSMSProvider
from backend.app.providers.sms.twilio_sms import TwilioSMSProvider


class SMSProviderFactory:
    @staticmethod
    def get_sms_provider() -> BaseSMSProvider:
        provider_type = os.getenv("SMS_PROVIDER", "simulation").lower()
        if provider_type == "twilio":
            return TwilioSMSProvider()
        return SimulationSMSProvider()

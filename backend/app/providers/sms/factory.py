"""
SMS & Mobile OTP Delivery Provider Factory.
Supports:
1. "ntfy" / "opensource": Open-Source mobile push notifications via ntfy.sh (Zero cost, instant mobile delivery)
2. "android": Open-Source Android SMS Gateway (uses any Android SIM card)
3. "fast2sms": Indian cellular SMS gateway
4. "twilio": Twilio international SMS gateway
5. "simulation": Local console log + dev code
"""
import os
from backend.app.providers.sms.base_sms import BaseSMSProvider
from backend.app.providers.sms.simulation_sms import SimulationSMSProvider
from backend.app.providers.sms.ntfy_sms import NtfySMSProvider
from backend.app.providers.sms.android_sms_gateway import AndroidSMSGatewayProvider
from backend.app.providers.sms.fast2sms import Fast2SMSProvider
from backend.app.providers.sms.twilio_sms import TwilioSMSProvider


class SMSProviderFactory:
    @staticmethod
    def get_sms_provider() -> BaseSMSProvider:
        provider_type = os.getenv("SMS_PROVIDER", "ntfy").lower()
        if provider_type in ("ntfy", "opensource", "open-source"):
            return NtfySMSProvider()
        elif provider_type in ("android", "android_gateway", "termux"):
            return AndroidSMSGatewayProvider()
        elif provider_type == "fast2sms":
            return Fast2SMSProvider()
        elif provider_type == "twilio":
            return TwilioSMSProvider()
        elif provider_type == "simulation":
            return SimulationSMSProvider()
        return NtfySMSProvider()

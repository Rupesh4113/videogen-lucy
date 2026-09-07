"""
NPCI Dynamic UPI QR Code & Payment Link Generator.
Generates compliant UPI intent URIs and base64 QR Code images for Indian bank settlements (Google Pay, PhonePe, Paytm, BHIM, CRED).
"""
import io
import base64
import urllib.parse
from typing import Dict, Any, Optional
from backend.app.config import settings


class UPIQRGenerator:
    """
    Generates dynamic UPI QR codes and payment deep links for instant direct bank account settlement.
    """

    @classmethod
    def generate_upi_intent_uri(
        cls,
        amount_inr: float,
        order_id: str,
        note: Optional[str] = None,
        merchant_vpa: Optional[str] = None,
        merchant_name: Optional[str] = None
    ) -> str:
        """
        Creates an NPCI-compliant UPI Intent URI.
        Format: upi://pay?pa=...&pn=...&am=...&cu=INR&tn=...&tr=...
        """
        vpa = merchant_vpa or settings.MERCHANT_UPI_VPA
        name = merchant_name or settings.MERCHANT_NAME
        tn = note or f"Videogen Lucy Video Credits #{order_id[:8]}"

        params = {
            "pa": vpa,
            "pn": name,
            "am": f"{amount_inr:.2f}",
            "cu": "INR",
            "tn": tn,
            "tr": order_id
        }

        query_str = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"upi://pay?{query_str}"

    @classmethod
    def generate_qr_code_image(cls, upi_uri: str) -> str:
        """
        Generates a high-contrast QR Code PNG image and returns it as a base64 Data URL.
        """
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(upi_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64_data}"
        except Exception as e:
            # Fallback for environments without PIL/qrcode
            encoded_uri = urllib.parse.quote(upi_uri)
            return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_uri}"

    @classmethod
    def get_upi_app_links(cls, upi_uri: str) -> Dict[str, str]:
        """
        Returns app-specific deep links for one-click payment on mobile devices.
        """
        raw_query = upi_uri.replace("upi://pay?", "")
        return {
            "generic": upi_uri,
            "gpay": f"gpay://upi/pay?{raw_query}",
            "phonepe": f"phonepe://pay?{raw_query}",
            "paytm": f"paytmmp://pay?{raw_query}",
            "bhim": f"bhim://pay?{raw_query}"
        }

    @classmethod
    def create_payment_payload(
        cls,
        amount_inr: float,
        order_id: str,
        plan_title: str,
        merchant_vpa: Optional[str] = None,
        merchant_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Constructs the complete UPI payment dictionary for frontend display.
        """
        vpa = merchant_vpa or settings.MERCHANT_UPI_VPA
        name = merchant_name or settings.MERCHANT_NAME
        uri = cls.generate_upi_intent_uri(
            amount_inr=amount_inr,
            order_id=order_id,
            note=f"Videogen {plan_title} Plan",
            merchant_vpa=vpa,
            merchant_name=name
        )
        qr_b64 = cls.generate_qr_code_image(uri)
        app_links = cls.get_upi_app_links(uri)

        return {
            "merchant_vpa": vpa,
            "merchant_name": name,
            "amount_inr": amount_inr,
            "order_id": order_id,
            "upi_uri": uri,
            "qr_code_data": qr_b64,
            "app_links": app_links,
            "bank_details": {
                "bank_name": settings.MERCHANT_BANK_NAME,
                "account_number": settings.MERCHANT_ACCOUNT_NO,
                "ifsc": settings.MERCHANT_IFSC,
                "swift": settings.MERCHANT_SWIFT,
                "account_holder": name
            }
        }

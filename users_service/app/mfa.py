import pyotp
import qrcode
from io import BytesIO
import base64
from typing import Tuple


def generate_mfa_secret() -> str:
    """Generate a new TOTP secret key"""
    return pyotp.random_base32()


def generate_totp_uri(username: str, secret: str, issuer: str = "SmartMeetingRoom") -> str:
    """Generate TOTP URI for QR code"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=issuer
    )


def generate_qr_code(uri: str) -> str:
    """Generate QR code image as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # Convert to base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify TOTP code"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 1 step before/after for clock drift


def get_current_totp_code(secret: str) -> str:
    """Get current TOTP code (for testing purposes)"""
    totp = pyotp.TOTP(secret)
    return totp.now()

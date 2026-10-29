"""QR en SVG para el alta TOTP: Google Authenticator lo escanea directo.

qrcode es la única dependencia (pure-python; el factory SVG no requiere PIL).
"""
import qrcode
import qrcode.image.svg


def uri_a_svg(uri: str) -> bytes:
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    return img.to_string()

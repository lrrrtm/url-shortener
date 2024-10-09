import base64
import hashlib


def generate_short_code(original_url: str) -> str:
    hash_object = hashlib.sha256(original_url.encode('utf-8'))

    short_code = base64.urlsafe_b64encode(hash_object.digest()[:6]).decode('utf-8')
    return short_code

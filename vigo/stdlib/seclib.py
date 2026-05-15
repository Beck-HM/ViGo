"""ViGo Standard Library: Security & Cryptography (seclib)
Provides hashing, encryption, JWT, password hashing, and secure random utilities.
Uses Python stdlib where possible (hashlib, hmac, secrets), optional PyJWT/cryptography.
"""
import hashlib
import hmac
import base64
import os
import secrets as _secrets
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register all seclib functions into the given ViGo environment."""

    # ── Hashing ──

    def md5(text):
        return hashlib.md5(str(text).encode()).hexdigest()

    def sha1(text):
        return hashlib.sha1(str(text).encode()).hexdigest()

    def sha256(text):
        return hashlib.sha256(str(text).encode()).hexdigest()

    def sha512(text):
        return hashlib.sha512(str(text).encode()).hexdigest()

    def blake2b(text, digest_size=32):
        return hashlib.blake2b(str(text).encode(), digest_size=int(digest_size)).hexdigest()

    def hash_file(filepath, algorithm="sha256"):
        h = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    # ── HMAC ──

    def hmac_sign(key, message, algorithm="sha256"):
        return hmac.new(
            str(key).encode(),
            str(message).encode(),
            algorithm
        ).hexdigest()

    def hmac_verify(key, message, signature, algorithm="sha256"):
        expected = hmac_sign(key, message, algorithm)
        return expected == signature

    # ── Base64 ──

    def base64_encode(data):
        return base64.b64encode(str(data).encode()).decode()

    def base64_decode(data):
        return base64.b64decode(str(data).encode()).decode()

    def base64_url_encode(data):
        return base64.urlsafe_b64encode(str(data).encode()).decode().rstrip("=")

    def base64_url_decode(data):
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data.encode()).decode()

    # ── Password hashing ──

    def bcrypt_hash(password, rounds=12):
        try:
            import bcrypt
            return bcrypt.hashpw(
                str(password).encode(),
                bcrypt.gensalt(int(rounds))
            ).decode()
        except ImportError:
            raise ViGoError("bcrypt not installed. Run: pip install bcrypt")

    def bcrypt_verify(password, hashed):
        try:
            import bcrypt
            return bcrypt.checkpw(
                str(password).encode(),
                str(hashed).encode()
            )
        except ImportError:
            raise ViGoError("bcrypt not installed. Run: pip install bcrypt")

    # ── AES Encryption ──

    def aes_encrypt(plaintext, key):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            key_bytes = str(key).encode().ljust(32)[:32]
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv))
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(str(plaintext).encode()) + padder.finalize()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            return base64.b64encode(iv + ciphertext).decode()
        except ImportError:
            raise ViGoError("cryptography not installed. Run: pip install cryptography")

    def aes_decrypt(ciphertext_b64, key):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            key_bytes = str(key).encode().ljust(32)[:32]
            raw = base64.b64decode(ciphertext_b64)
            iv, ciphertext = raw[:16], raw[16:]
            cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_data) + unpadder.finalize()
            return plaintext.decode()
        except ImportError:
            raise ViGoError("cryptography not installed. Run: pip install cryptography")

    # ── JWT ──

    def jwt_encode(payload, secret, algorithm="HS256"):
        try:
            import jwt
            return jwt.encode(
                payload if isinstance(payload, dict) else {"data": payload},
                str(secret),
                algorithm=algorithm
            )
        except ImportError:
            raise ViGoError("PyJWT not installed. Run: pip install pyjwt")

    def jwt_decode(token, secret, algorithms=None):
        try:
            import jwt
            if algorithms is None:
                algorithms = ["HS256"]
            return jwt.decode(str(token), str(secret), algorithms=algorithms)
        except ImportError:
            raise ViGoError("PyJWT not installed. Run: pip install pyjwt")

    # ── Secure random ──

    def secure_random_bytes(n):
        return _secrets.token_bytes(int(n)).hex()

    def secure_random_int(min_val, max_val):
        return _secrets.randbelow(int(max_val) - int(min_val) + 1) + int(min_val)

    def secure_random_string(length=32):
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(_secrets.choice(alphabet) for _ in range(int(length)))

    def secure_uuid():
        return str(_secrets.token_hex(16))

    # ── Registration ──

    env.define("md5", BuiltinFunction(md5, "md5"))
    env.define("sha1", BuiltinFunction(sha1, "sha1"))
    env.define("sha256", BuiltinFunction(sha256, "sha256"))
    env.define("sha512", BuiltinFunction(sha512, "sha512"))
    env.define("blake2b", BuiltinFunction(blake2b, "blake2b"))
    env.define("hash_file", BuiltinFunction(hash_file, "hash_file"))
    env.define("hmac_sign", BuiltinFunction(hmac_sign, "hmac_sign"))
    env.define("hmac_verify", BuiltinFunction(hmac_verify, "hmac_verify"))
    env.define("base64_encode", BuiltinFunction(base64_encode, "base64_encode"))
    env.define("base64_decode", BuiltinFunction(base64_decode, "base64_decode"))
    env.define("base64_url_encode", BuiltinFunction(base64_url_encode, "base64_url_encode"))
    env.define("base64_url_decode", BuiltinFunction(base64_url_decode, "base64_url_decode"))
    env.define("bcrypt_hash", BuiltinFunction(bcrypt_hash, "bcrypt_hash"))
    env.define("bcrypt_verify", BuiltinFunction(bcrypt_verify, "bcrypt_verify"))
    env.define("aes_encrypt", BuiltinFunction(aes_encrypt, "aes_encrypt"))
    env.define("aes_decrypt", BuiltinFunction(aes_decrypt, "aes_decrypt"))
    env.define("jwt_encode", BuiltinFunction(jwt_encode, "jwt_encode"))
    env.define("jwt_decode", BuiltinFunction(jwt_decode, "jwt_decode"))
    env.define("secure_random_bytes", BuiltinFunction(secure_random_bytes, "secure_random_bytes"))
    env.define("secure_random_int", BuiltinFunction(secure_random_int, "secure_random_int"))
    env.define("secure_random_string", BuiltinFunction(secure_random_string, "secure_random_string"))
    env.define("secure_uuid", BuiltinFunction(secure_uuid, "secure_uuid"))
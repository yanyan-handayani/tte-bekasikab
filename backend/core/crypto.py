import hashlib
import logging
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_FERNET = None
_KEY_FPR = None  # fingerprint buat verifikasi key sama/beda antar proses

def _get_key() -> str:
    key = getattr(settings, "PDP_ENC_KEY", None)
    if not key:
        raise RuntimeError("PDP_ENC_KEY belum diset di settings")

    # normalize: hapus whitespace/newline dari .env
    if isinstance(key, bytes):
        key = key.decode("utf-8", errors="ignore")
    key = str(key).strip()
    return key

def _fernet() -> Fernet:
    global _FERNET, _KEY_FPR
    key = _get_key()

    # fingerprint key (tidak bocorkan key asli)
    fpr = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    # cache Fernet selama key sama
    if _FERNET is None or _KEY_FPR != fpr:
        _FERNET = Fernet(key)
        _KEY_FPR = fpr
        logger.info("PDP Fernet initialized (key_fpr=%s)", _KEY_FPR)

    return _FERNET

def encrypt_str(s: str) -> str:
    if s is None:
        return None
    token = _fernet().encrypt(str(s).encode("utf-8"))
    return token.decode("utf-8")

def decrypt_str(token: str) -> str:
    if token is None:
        return None
    try:
        raw = _fernet().decrypt(str(token).encode("utf-8"))
        return raw.decode("utf-8")
    except InvalidToken:
        # ini yang lagi terjadi di admin kamu: ciphertext ada, tapi decrypt gagal
        logger.warning("Decrypt failed: InvalidToken (key_fpr=%s, token_head=%s)", _KEY_FPR, str(token)[:16])

        # mode debug cepat: kalau mau kelihatan errornya (opsional)
        # if settings.DEBUG:
        #     raise

        return None
    except Exception as e:
        logger.exception("Decrypt failed: unexpected error (key_fpr=%s): %s", _KEY_FPR, e)
        # if settings.DEBUG:
        #     raise
        return None

def hash_lookup(s: str) -> str:
    if s is None:
        return None
    norm = str(s).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

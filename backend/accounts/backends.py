# accounts/backends.py
import hashlib
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

def _is_hex(s: str) -> bool:
    try:
        int(s, 16)
        return True
    except Exception:
        return False

def detect_algo(legacy_hash: str) -> str | None:
    if not legacy_hash:
        return None
    h = legacy_hash.strip().lower()
    if len(h) == 32 and _is_hex(h):
        return "md5"
    if len(h) == 40 and _is_hex(h):
        return "sha1"
    return None

def hash_with_algo(raw: str, algo: str) -> str:
    raw_b = (raw or "").encode("utf-8")
    if algo == "md5":
        return hashlib.md5(raw_b).hexdigest()
    if algo == "sha1":
        return hashlib.sha1(raw_b).hexdigest()
    raise ValueError("unsupported algo")

class LegacyPinBackend(ModelBackend):
    """
    Jika user masih punya legacy_pin_hash, cek raw PIN terhadap hash legacy,
    lalu upgrade ke password Django.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        # Kalau sudah punya password Django yang valid, pakai mekanisme standar
        if user.has_usable_password():
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None

        # Kalau belum usable, coba legacy
        legacy_hash = (user.legacy_pin_hash or "").strip().lower()
        if not legacy_hash:
            return None

        algo = (user.legacy_pin_algo or "").strip().lower() or detect_algo(legacy_hash)
        if not algo:
            return None

        if hash_with_algo(password, algo) == legacy_hash and self.user_can_authenticate(user):
            # Upgrade ke hash Django
            user.set_password(password)
            user.legacy_pin_hash = None
            user.legacy_pin_algo = None
            user.save(update_fields=["password", "legacy_pin_hash", "legacy_pin_algo"])
            return user

        return None

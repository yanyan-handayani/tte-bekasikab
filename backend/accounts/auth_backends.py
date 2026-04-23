from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from core.crypto import hash_lookup

User = get_user_model()

class NIPHashBackend(ModelBackend):
    """
    Login menggunakan NIP (plaintext input), dicari via username_hash.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        nip = (username or "").strip().replace(" ", "")
        if not nip or password is None:
            return None

        h = hash_lookup(nip)
        try:
            user = User.objects.get(username_hash=h, is_active=True)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

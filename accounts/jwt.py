import pyotp
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from core.crypto import hash_lookup


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        must_change = bool(getattr(user, "must_change_password", False))
        expired = bool(user.password_is_expired())

        token["force_change_password"] = must_change or expired
        token["pwd_status"] = (
            "password_change_required" if must_change
            else "password_expired" if expired
            else "ok"
        )
        return token

    def validate(self, attrs):
        request = self.context.get("request")

        username = attrs.get(self.username_field)
        if isinstance(username, str):
            username = username.strip()
            attrs[self.username_field] = username
        password = attrs.get("password")

        UserModel = get_user_model()

        nip = (username or "").strip().replace(" ", "")
        user = None
        if nip:
            h = hash_lookup(nip)
            user = UserModel.objects.filter(username_hash=h, is_active=True).only(
                "id",
                "username",
                "full_name",
                "lockout_until",
                "failed_login_count",
                "twofa_enabled",
                "twofa_secret",
                "must_change_password",
                "password_changed_at",
            ).first()

        if user and user.lockout_until and user.lockout_until > timezone.now():
            raise serializers.ValidationError(
                {"detail": "Akun terkunci sementara karena terlalu banyak percobaan login."}
            )

        if user and user.lockout_until and user.lockout_until <= timezone.now() and user.failed_login_count:
            user.failed_login_count = 0
            user.lockout_until = None
            user.save(update_fields=["failed_login_count", "lockout_until"])

        auth_user = authenticate(request=request, username=username, password=password)

        if auth_user is None:
            if user:
                user.register_failed_login(max_attempts=3, lock_minutes=15)
                user.refresh_from_db(fields=["failed_login_count", "lockout_until"])
                if user.lockout_until and user.lockout_until > timezone.now():
                    raise serializers.ValidationError(
                        {"detail": "Akun terkunci sementara karena terlalu banyak percobaan login."}
                    )

            raise serializers.ValidationError({"detail": "Username/password salah."})

        if getattr(auth_user, "twofa_enabled", False):
            otp = (request.data.get("otp") if request else None) or attrs.get("otp")
            otp = (str(otp).strip() if otp is not None else "")

            if not otp:
                raise serializers.ValidationError({
                    "detail": "OTP wajib untuk akun ini.",
                    "code": "2fa_required"
                })

            secret = getattr(auth_user, "twofa_secret", None)
            if not secret:
                raise serializers.ValidationError({
                    "detail": "2FA secret belum ada. Setup ulang 2FA."
                })

            totp = pyotp.TOTP(secret)
            if not totp.verify(otp, valid_window=1):
                auth_user.register_failed_login(max_attempts=3, lock_minutes=15)
                raise serializers.ValidationError({"detail": "OTP salah."})

        # sukses auth → reset counter login gagal
        auth_user.register_success_login()

        # tetap generate token walaupun password expired / wajib ganti
        data = super().validate(attrs)

        force_change = False
        reason = None
        detail = None

        if getattr(auth_user, "must_change_password", False):
            force_change = True
            reason = "password_change_required"
            detail = "Password wajib diganti terlebih dahulu."
        elif auth_user.password_is_expired():
            force_change = True
            reason = "password_expired"
            detail = "Password Anda sudah kedaluwarsa. Silakan ganti password."

        data["force_change_password"] = force_change
        data["code"] = reason
        data["detail"] = detail
        data["user"] = {
            "id": auth_user.id,
            "username": auth_user.username,
            "full_name": getattr(auth_user, "full_name", ""),
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
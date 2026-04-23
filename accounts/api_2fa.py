import base64
import io

import pyotp
import qrcode
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class TwoFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.twofa_enabled:
            return Response(
                {"detail": "2FA sudah aktif. Nonaktifkan dulu untuk setup ulang."},
                status=400,
            )

        # generate new secret every setup
        secret = pyotp.random_base32()
        user.twofa_secret = secret
        user.twofa_enabled = False
        user.save(update_fields=["twofa_secret", "twofa_enabled"])

        issuer = "TTE"
        label = (user.username or "").strip()  # rapikan label (hindari spasi)
        uri = pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)

        # generate QR PNG bytes
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        fmt = (request.query_params.get("format") or "").lower()

        # opsi 1: base64 JSON
        if fmt in ("base64", "b64", "json"):
            b64 = base64.b64encode(png_bytes).decode("ascii")
            return Response(
                {
                    "qr_png_base64": b64,
                    # kalau kamu mau, boleh juga kirim uri untuk debug:
                    # "otpauth_uri": uri,
                },
                status=status.HTTP_200_OK,
            )

        # opsi 2 (default): binary PNG (blob)
        resp = HttpResponse(png_bytes, content_type="image/png")
        resp["Cache-Control"] = "no-store"
        return resp


class TwoFAEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        otp = str(request.data.get("otp", "")).strip()

        if not user.twofa_secret:
            return Response({"detail": "2FA secret belum ada. Jalankan setup dulu."}, status=400)
        if not otp:
            return Response({"detail": "OTP wajib."}, status=400)

        totp = pyotp.TOTP(user.twofa_secret)
        if not totp.verify(otp, valid_window=1):
            return Response({"detail": "OTP salah."}, status=400)

        user.twofa_enabled = True
        user.save(update_fields=["twofa_enabled"])
        return Response({"detail": "2FA aktif."}, status=200)


class TwoFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        otp = str(request.data.get("otp", "")).strip()

        if user.twofa_enabled:
            if not otp:
                return Response({"detail": "OTP wajib untuk menonaktifkan 2FA."}, status=400)
            totp = pyotp.TOTP(user.twofa_secret or "")
            if not totp.verify(otp, valid_window=1):
                return Response({"detail": "OTP salah."}, status=400)

        user.twofa_enabled = False
        user.twofa_secret = None
        user.twofa_backup_codes = None
        user.save(update_fields=["twofa_enabled", "twofa_secret", "twofa_backup_codes"])
        return Response({"detail": "2FA nonaktif."}, status=200)

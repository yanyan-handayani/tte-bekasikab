from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import MstJabatan, MstDataPegawai, TaJabatan
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.conf import settings
from django.core.mail import send_mail
from accounts.models import EmailSendLog
from core.crypto import hash_lookup
import re
from django.utils import timezone


def validate_strong_password(password: str):
    errors = []

    if len(password) < 8:
        errors.append("Minimal 8 karakter.")

    if not re.search(r"[A-Z]", password):
        errors.append("Harus mengandung huruf besar.")

    if not re.search(r"[a-z]", password):
        errors.append("Harus mengandung huruf kecil.")

    if not re.search(r"[0-9]", password):
        errors.append("Harus mengandung angka.")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\\[\]]", password):
        errors.append("Harus mengandung karakter khusus.")

    if errors:
        raise ValueError(errors)


User = get_user_model()
token_generator = PasswordResetTokenGenerator()


def _get_client_ip(request) -> str | None:
    # aman untuk reverse proxy kalau memang diset
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


def _derive_email_from_user(user) -> str | None:
    """
    Kalau user.email kosong, bikin: nip@bekasikab.go.id
    Fallback: nik@bekasikab.go.id
    """
    email = (getattr(user, "email", None) or "").strip()
    if email:
        return email

    peg = getattr(user, "pegawai", None)
    if not peg:
        return None

    nip = (getattr(peg, "nip", None) or "").strip()
    nik = (getattr(peg, "nik", None) or "").strip()

    ident = nip or nik
    if not ident:
        return None

    domain = getattr(settings, "DEFAULT_RESET_EMAIL_DOMAIN", "bekasikab.go.id")
    return f"{ident}@{domain}".lower()


def as_primitive_fk(val):
    if val is None:
        return None
    if hasattr(val, "pk"):
        return val.pk
    return val


def pick_jabatan(id_jabatan: int, instansi_id: int):
    qs = MstJabatan.objects.filter(id_jabatan=id_jabatan)
    if instansi_id:
        qs = qs.filter(instansi_id=instansi_id)

    # pilih deterministik kalau ternyata ada duplikat id_jabatan
    return qs.order_by("level_jabatan", "no_urut", "parent_id").first()

def get_pejabat_for_jabatan(jabatan_id: int, instansi_id: int | None = None, limit: int = 10):
    from django.utils import timezone
    from django.db.models import Q

    today = timezone.localdate()

    def serialize_ta(qs, source_label):
        rows = []
        seen = set()
        for r in qs[:limit]:
            p = r.nip
            if not p or p.id in seen:
                continue
            seen.add(p.id)
            rows.append({
                "id": p.id,
                "nip": p.nip,
                "nama": p.nama_lengkap,
                "plt": True,
                "sumber": source_label,
                "ta_jabatan_id": r.id,
                "jabatan_awal": r.jabatan_awal,
                "jabatan_akhir": r.jabatan_akhir,
                "pegawai_instansi_id": p.id_instansi_id,
            })
        return rows

    base_ta = (
        TaJabatan.objects
        .filter(
            id_jabatan_id=jabatan_id,
            status=True,
            nip__is_active=True,
        )
        .filter(
            Q(jabatan_akhir__isnull=True) | Q(jabatan_akhir__gte=today)
        )
        .select_related("nip", "id_jabatan")
        .order_by("-jabatan_awal", "-id")
    )

    # 1) coba dalam instansi yang sama
    if instansi_id:
        rows = serialize_ta(
            base_ta.filter(nip__id_instansi_id=instansi_id),
            "ta_jabatan_same_instansi"
        )
        if rows:
            return rows

    rows = serialize_ta(base_ta, "ta_jabatan_any_instansi")
    if rows:
        return rows

    def serialize_pegawai(qs, source_label):
        rows = []
        for p in qs[:limit]:
            rows.append({
                "id": p.id,
                "nip": p.nip,
                "nama": p.nama_lengkap,
                "plt": False,
                "sumber": source_label,
                "ta_jabatan_id": None,
                "jabatan_awal": None,
                "jabatan_akhir": None,
                "pegawai_instansi_id": p.id_instansi_id,
            })
        return rows

    base_pegawai = MstDataPegawai.objects.filter(
        id_jabatan_id=jabatan_id,
        is_active=True,
    )

    # 3) fallback mst_datapegawai dalam instansi sama
    if instansi_id:
        rows = serialize_pegawai(
            base_pegawai.filter(id_instansi_id=instansi_id),
            "mst_datapegawai_same_instansi"
        )
        if rows:
            return rows

    # 4) fallback mst_datapegawai tanpa filter instansi
    rows = serialize_pegawai(base_pegawai, "mst_datapegawai_any_instansi")
    return rows

def build_atasan_chain(peg, max_depth=20, max_pejabat_per_level=10):
    if not peg or not getattr(peg, "id_jabatan_id", None):
        return []

    instansi_id = getattr(peg, "id_instansi_id", None)
    current_jabatan_id = peg.id_jabatan_id

    visited = {current_jabatan_id}
    out = []

    for _ in range(max_depth):
        j = pick_jabatan(current_jabatan_id, instansi_id)
        if not j:
            break

        parent_id = j.parent_id
        if not parent_id or parent_id == 0 or parent_id in visited:
            break
        visited.add(parent_id)

        parent_j = pick_jabatan(parent_id, instansi_id)
        if not parent_j:
            break

        out.append(
            {
                "jabatan": {
                    "id_jabatan": parent_j.id_jabatan,
                    "nama_jabatan": parent_j.nama_jabatan,
                    "level_jabatan": parent_j.level_jabatan,
                },
                "pejabat": get_pejabat_for_jabatan(
                    jabatan_id=parent_id,
                    instansi_id=instansi_id,
                    limit=max_pejabat_per_level,
                ),
            }
        )

        current_jabatan_id = parent_id

    return out


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        peg = getattr(u, "pegawai", None)

        data_pegawai = None
        if peg:
            instansi_val = getattr(peg, "id_instansi", None)

            data_pegawai = {
                "id": getattr(peg, "id", None),
                "nip": getattr(peg, "nip", None),
                "nama": getattr(peg, "nama_lengkap", None),
                "id_jabatan": getattr(peg, "id_jabatan_id", None),
                "id_instansi": as_primitive_fk(instansi_val),
                "instansi": (
                     {
                         "id": getattr(instansi_val, "pk", None),
                         "nama": getattr(instansi_val, "nama", None),
                     }
                     if hasattr(instansi_val, "pk")
                     else None
                 ),
                 "atasan": build_atasan_chain(peg),
             }

        return Response(
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "pegawai": data_pegawai,
                 "twofa": {
                     "enabled": bool(getattr(u, "twofa_enabled", False)),
                     "configured": bool(getattr(u, "twofa_secret", None)),  # secret sudah ada/belum
                 },
                 "is_staff": u.is_staff,
                 "is_superuser": u.is_superuser,
             }
        )


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password/reset/request
    body: { "username": "..." } atau { "email": "..." }

    Return selalu 200 untuk mencegah user enumeration.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        raw_username = (request.data.get("username") or "").strip()
        raw_email = (request.data.get("email") or "").strip().lower()
        raw_nip = raw_email.split("@")[0].strip() if raw_email else ""

        user = None
        to_email = None

        # 1) Cari user via username_hash
        #    karena input username biasanya NIP/NIK tapi di DB disimpan hash
        if raw_username:
            uhash = hash_lookup(raw_username)
            if uhash:
                user = (
                    User.objects
                    .filter(username_hash=uhash)
                    .select_related("pegawai")
                    .first()
                )

        # 2) Kalau input email diberikan, cek NIP di tabel pegawai
        #    Jika cocok, kirim ke <nip>@bekasikab.go.id
        if not user and raw_email.endswith("@bekasikab.go.id") and raw_nip:
            nip_hash = hash_lookup(raw_nip)
            if nip_hash:
                user = (
                    User.objects
                    .filter(pegawai__nip_hash=nip_hash)
                    .select_related("pegawai")
                    .first()
                )
                if user:
                    to_email = f"{raw_nip}@bekasikab.go.id"

        # 3) Fallback: cari via email user.email
        if not user and raw_email:
            user = (
                User.objects
                .filter(email__iexact=raw_email)
                .select_related("pegawai")
                .first()
            )

        # response selalu silent (anti enumeration)
        resp = {
            "ok": True,
            "message": "Jika akun terdaftar, link reset password akan dikirim ke email.",
        }

        if not user:
            return Response(resp, status=status.HTTP_200_OK)

        subject = "Reset Password - TTE Bekasi"

        # bila belum ditentukan dari tahap NIP, fallback ke derive biasa
        if not to_email:
            to_email = _derive_email_from_user(user)

        # kalau tidak dapat email target, tetap log sebagai SKIPPED, response tetap 200
        if not to_email:
            EmailSendLog.objects.create(
                purpose=EmailSendLog.Purpose.PASSWORD_RESET,
                status=EmailSendLog.Status.SKIPPED,
                user=user,
                to_email=None,
                subject=subject,
                error_message="No target email (user.email empty and pegawai nip/nik empty).",
                request_ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )
            return Response(resp, status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        frontend = getattr(settings, "FRONTEND_URL", "").rstrip("/")
        reset_link = f"{frontend}/reset-password?uid={uid}&token={token}"

        body = (
            "Anda meminta reset password.\n\n"
            f"Silakan klik tautan berikut untuk mengatur password baru:\n{reset_link}\n\n"
            "Jika Anda tidak merasa meminta reset password, abaikan email ini."
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[to_email],
                fail_silently=False,
            )

            EmailSendLog.objects.create(
                purpose=EmailSendLog.Purpose.PASSWORD_RESET,
                status=EmailSendLog.Status.SENT,
                user=user,
                to_email=to_email,
                subject=subject,
                error_message=None,
                request_ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )
        except Exception as e:
            EmailSendLog.objects.create(
                purpose=EmailSendLog.Purpose.PASSWORD_RESET,
                status=EmailSendLog.Status.FAILED,
                user=user,
                to_email=to_email,
                subject=subject,
                error_message=str(e),
                request_ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )

        return Response(resp, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password/reset/confirm
    body: { "uid": "...", "token": "...", "new_password": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uid or not token or not new_password:
            return Response({"ok": False, "message": "uid/token/new_password wajib."}, status=400)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({"ok": False, "message": "Token tidak valid."}, status=400)

        if not token_generator.check_token(user, token):
            return Response({"ok": False, "message": "Token tidak valid / kadaluarsa."}, status=400)

        try:
            validate_password(new_password, user=user)
        except Exception as e:
            # e bisa ValidationError, tampilkan ringkas
            return Response({"ok": False, "message": "Password tidak memenuhi aturan.", "detail": getattr(e, "messages", [str(e)])}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"ok": True, "message": "Password berhasil direset."}, status=200)


class PasswordChangeView(APIView):
    """
    POST /api/auth/password/change  (harus login)
    body: { "old_password": "...", "new_password": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({"ok": False, "message": "old_password dan new_password wajib."}, status=400)

        if not user.check_password(old_password):
            return Response({"ok": False, "message": "Password lama salah."}, status=400)

        try:
            validate_strong_password(new_password)

            validate_password(new_password, user=user)

        except ValueError as e:
            return Response({
                "ok": False,
                "message": "Password tidak memenuhi aturan.",
                "detail": e.args[0] if isinstance(e.args[0], list) else [str(e)]
            }, status=400)

        except Exception as e:
            return Response({
                "ok": False,
                "message": "Password tidak memenuhi aturan.",
                "detail": getattr(e, "messages", [str(e)])
            }, status=400)

        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.must_change_password = False

        user.save(update_fields=["password", "password_changed_at", "must_change_password"])

        return Response({"ok": True, "message": "Password berhasil diubah."}, status=200)
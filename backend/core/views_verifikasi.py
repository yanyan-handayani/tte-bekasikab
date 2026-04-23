# core/views_verifikasi.py
import mimetypes
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.core.files.storage import default_storage

from core.models import Surat
from core.models_verifikasi import SuratVerifikasi
from django.db.models import F


def _pick_pdf_field(surat: Surat):
    """
    Prioritas: signed -> unsigned -> file_surat (upload awal).
    """
    if getattr(surat, "file_signed", None):
        if surat.file_signed and getattr(surat.file_signed, "name", ""):
            return surat.file_signed
    if getattr(surat, "file_unsigned", None):
        if surat.file_unsigned and getattr(surat.file_unsigned, "name", ""):
            return surat.file_unsigned
    if getattr(surat, "file_surat", None):
        if surat.file_surat and getattr(surat.file_surat, "name", ""):
            return surat.file_surat
    return None


@require_GET
def verifikasi_view(request, token: str):
    v = get_object_or_404(SuratVerifikasi, token=token, is_active=True)

    v.hit_count = (v.hit_count or 0) + 1
    v.last_access_at = timezone.now()
    v.save(update_fields=["hit_count", "last_access_at"])

    s = v.surat

    # Ambil hanya yang sudah tanda tangan
    penandatangan = (
        s.tahapan_set
         .select_related("pejabat")
         .filter(sign_date__isnull=False)
         .order_by("seq_tahapan", "id_tahapan")
    )

    return render(request, "tte/verifikasi_surat.html", {
        "token": token,
        "surat": s,
        "penandatangan_list": penandatangan,
    })

@require_GET
def verifikasi_pdf(request, token: str):
    """
    URL: /verifikasi/<token>/pdf
    Render PDF inline di browser (tanpa presigned URL).
    """
    v = get_object_or_404(SuratVerifikasi, token=token, is_active=True)
    s = v.surat

    ffield = _pick_pdf_field(s)
    if not ffield:
        raise Http404("File PDF surat tidak tersedia")

    storage_name = ffield.name  # key/path di MinIO
    if not default_storage.exists(storage_name):
        raise Http404("File PDF tidak ditemukan di storage")

    f = default_storage.open(storage_name, "rb")

    filename = f"surat_{s.id_surat}.pdf"
    content_type, _ = mimetypes.guess_type(filename)
    content_type = content_type or "application/pdf"

    resp = FileResponse(f, content_type=content_type)
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@require_GET
def lihat_surat_legacy(request, id_surat: int):
    surat = get_object_or_404(Surat, id_surat=id_surat)

    v = (SuratVerifikasi.objects
         .filter(surat=surat, is_active=True)
         .order_by("-created_at")
         .first())

    if not v:
        v = SuratVerifikasi.objects.create(
            token=SuratVerifikasi.new_token(),
            surat=surat,
            is_active=True,
        )

    return redirect(reverse("tte_verifikasi", args=[v.token]))
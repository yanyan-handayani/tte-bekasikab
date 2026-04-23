import hashlib
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from core.models_verifikasi import SuratVerifikasi
from core.utils.pdf_stamp import stamp_unsigned_pdf
from core.utils.specimen_generator import build_generated_specimen_for_pegawai
import io
from pypdf import PdfReader

from core.models import Surat, SuratTahapan, Setting, MstDataPegawai, SuratTemplateSpecimenSlot
from core.utils.pdf_stamp import (
    stamp_unsigned_pdf,
    find_text_markers_all,
    find_text_occurrences_all,
    _pointer_targets,
    resolve_page_index,
)

SIGN_TYPE_PARAF = 1
SIGN_TYPE_TTD = 2
SIGN_STATUS_SUDAH = 2


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _pick(tpl, setting, attr, default=None):
    if tpl is not None:
        v = getattr(tpl, attr, None)
        if v not in (None, ""):
            return v
    if setting is not None:
        v2 = getattr(setting, attr, None)
        if v2 not in (None, ""):
            return v2
    return default


def _resolve_page(v):
    if v is None:
        return "last"
    try:
        iv = int(v)
    except Exception:
        return "last"
    return "last" if iv == 0 else iv


def _read_filefield_bytes(ff) -> bytes | None:
    if not ff:
        return None
    try:
        ff.open("rb")
        return ff.read()
    except Exception:
        return None
    finally:
        try:
            ff.close()
        except Exception:
            pass

def _sort_lr_tb(markers):
    return sorted(markers, key=lambda m: (m[0], -m[2], m[1]))


def _marker_targets(markers, *, w: float, h: float, offset=(0, 0), cover_marker=True):
    out = []
    ox = float(offset[0] or 0)
    oy = float(offset[1] or 0)

    for (pi, mx, my, mw, mh, _, _) in markers:
        marker_cx = mx + (mw / 2.0)
        marker_cy = my + (mh / 2.0)
        x = marker_cx - (w / 2.0) + ox
        y = marker_cy - (h / 2.0) + oy
        cover = (mx, my, mw, mh) if cover_marker else None

        out.append({
            "page": pi,
            "x": x,
            "y": y,
            "cover": cover,
            "w": w,
            "h": h,
        })
    return out


def _build_slot_target(pdf_bytes, num_pages, slot, default_w, default_h):
    slot_w = float(slot.width or default_w)
    slot_h = float(slot.height or default_h)
    offset = (int(slot.offset_x or 0), int(slot.offset_y or 0))
    placement_type = (slot.placement_type or "pointer").strip().lower()

    if placement_type == "marker" and slot.marker_text:
        marks = find_text_markers_all(pdf_bytes, slot.marker_text)
        marks = _sort_lr_tb([m for m in marks if m])
        if marks:
            tgts = _marker_targets(marks[:1], w=slot_w, h=slot_h, offset=offset, cover_marker=True)
            if tgts:
                return tgts[0]

    if placement_type == "pointer" and slot.pointer_text:
        marks = find_text_occurrences_all(pdf_bytes, slot.pointer_text)
        marks = _sort_lr_tb([m for m in marks if m])
        if marks:
            tgts = _pointer_targets(
                marks[:1],
                w=slot_w,
                h=slot_h,
                mode=(slot.pointer_mode or "below"),
                offset=offset,
            )
            if tgts:
                return tgts[0]

    page_idx = resolve_page_index(slot.fallback_page or "last", num_pages)
    return {
        "page": page_idx,
        "x": float(slot.fallback_x or 250),
        "y": float(slot.fallback_y or 80),
        "cover": None,
        "w": slot_w,
        "h": slot_h,
    }

@transaction.atomic
def action_paraf(
    *,
    surat_id: int,
    pejabat_id: int,
    verify_base_url: str,
    paraf_index: int = 0,
    setting_id: int | None = None,
    qr_fallback=None,
    ttd_fallback=None,
):
    surat = Surat.objects.select_for_update().get(id_surat=surat_id)

    tahapan = (
        SuratTahapan.objects.select_for_update()
        .filter(surat=surat, pejabat_id=pejabat_id, sign_date__isnull=True)
        .order_by("seq_tahapan", "id_tahapan")
        .first()
    )
    if not tahapan:
        raise ValueError("Tidak ada tahapan aktif untuk pejabat ini atau sudah selesai.")
    if int(tahapan.sign_type_ref_id or 0) != SIGN_TYPE_PARAF:
        raise ValueError("Tahapan ini bukan PARAF.")

    setting = Setting.objects.filter(id_set=setting_id).first() if setting_id else None
    if not setting:
        setting = Setting.objects.order_by("id_set").first()

    tpl = getattr(surat, "template_ref", None)
    if tpl and getattr(tpl, "is_active", True) is False:
        tpl = None

    tahapan.sign_status_ref_id = SIGN_STATUS_SUDAH
    tahapan.sign_date = timezone.now()
    tahapan.save(update_fields=["sign_status_ref_id", "sign_date"])

    # jangan restamp kalau unsigned sudah ada
    if surat.file_unsigned:
        return {
            "surat_id": surat.id_surat,
            "tahapan_id": tahapan.id_tahapan,
            "unsigned_path": getattr(surat.file_unsigned, "name", None),
            "stamped": False,
            "note": "Unsigned sudah ada; paraf hanya update status.",
        }

    v = (
        SuratVerifikasi.objects
        .filter(surat=surat, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if not v:
        v = SuratVerifikasi.objects.create(
            token=SuratVerifikasi.new_token(),
            surat=surat,
            is_active=True,
        )

    qr_payload = f"{verify_base_url.rstrip('/')}/{v.token}"

    if not surat.file_surat:
        raise ValueError("file_surat belum ada.")

    pdf_bytes = _read_filefield_bytes(surat.file_surat)
    if not pdf_bytes:
        raise ValueError("file_surat kosong / gagal dibaca dari storage.")

    logo_bytes = _read_filefield_bytes(getattr(setting, "qr_logo", None))

    # # semua signer TTD
    # tte_steps = list(
    #     SuratTahapan.objects.filter(surat=surat, sign_type_ref_id=SIGN_TYPE_TTD)
    #     .order_by("seq_tahapan", "id_tahapan")
    #     .values_list("pejabat_id", flat=True)
    # )

    specimen_mode = _pick(tpl, setting, "specimen_mode", "upload")
    marker_qr = _pick(tpl, setting, "qr_marker_text", "[QR]")
    marker_ttd = _pick(tpl, setting, "ttd_marker_text", "[TTD{n}]")
    marker_specimen = _pick(tpl, setting, "specimen_marker_text", "[SPESIMEN{n}]")
    specimen_pointer_text = _pick(tpl, setting, "specimen_pointer_text", None)
    specimen_pointer_mode = _pick(tpl, setting, "specimen_pointer_mode", "below")

    # paksa semua marker agar QR dan specimen tidak cuma 1
    stamp_mode = "all_markers"

    qr_w = int(_pick(tpl, setting, "qr_width", getattr(setting, "qr_width", 110)) or 110)
    qr_h = int(_pick(tpl, setting, "qr_height", getattr(setting, "qr_height", 110)) or 110)
    qr_x = int(_pick(tpl, setting, "qr_x", getattr(setting, "qr_fallback_x", 110)) or 110)
    qr_y = int(_pick(tpl, setting, "qr_y", getattr(setting, "qr_fallback_y", 110)) or 110)

    ttd_w = int(_pick(tpl, setting, "ttd_width", getattr(setting, "ttd_width", 120)) or 120)
    ttd_h = int(_pick(tpl, setting, "ttd_height", getattr(setting, "ttd_height", 60)) or 60)

    specimen_w = int(_pick(tpl, setting, "specimen_width", 260) or 260)
    specimen_h = int(_pick(tpl, setting, "specimen_height", 95) or 95)

    specimen_offset_x = int(_pick(tpl, setting, "specimen_offset_x", 0) or 0)
    specimen_offset_y = int(_pick(tpl, setting, "specimen_offset_y", 0) or 0)

    qr_fb = qr_fallback or {
        "page": _resolve_page(getattr(setting, "qr_fallback_page", 0) if setting else 0),
        "x": qr_x,
        "y": qr_y,
        "w": qr_w,
        "h": qr_h,
    }

    ttd_fb = ttd_fallback or {
        "page": _resolve_page(getattr(setting, "ttd_fallback_page", 0) if setting else 0),
        "x": int(getattr(setting, "ttd_fallback_x", 320) if setting else 320),
        "y": int(getattr(setting, "ttd_fallback_y", 80) if setting else 80),
        "w": ttd_w,
        "h": ttd_h,
    }

    specimen_fb = {
        "page": _resolve_page(getattr(setting, "ttd_fallback_page", 0) if setting else 0),
        "x": int(getattr(setting, "ttd_fallback_x", 250) if setting else 250),
        "y": int(getattr(setting, "ttd_fallback_y", 80) if setting else 80),
        "w": specimen_w,
        "h": specimen_h,
    }

    # # build specimen list
    # specimen_list: list[bytes] = []
    # for pid in tte_steps:
    #     p = MstDataPegawai.objects.filter(id=pid).select_related("id_jabatan").first()
    #     if not p:
    #         continue

    #     b = None
    #     if specimen_mode == "generated":
    #         try:
    #             b = build_generated_specimen_for_pegawai(
    #                 p,
    #                 surat_template=tpl,
    #                 logo_png_bytes=logo_bytes,
    #             )
    #         except Exception:
    #             b = None

    #     if not b:
    #         b = _read_filefield_bytes(getattr(p, "specimen_ttd", None)) \
    #             or _read_filefield_bytes(getattr(p, "specimen_paraf", None))

    #     if b:
    #         specimen_list.append(b)

    # ambil semua signer TTE (urut seq) untuk ditempel spesimennya di unsigned
    tte_steps = list(
        SuratTahapan.objects.filter(surat=surat, sign_type_ref_id=SIGN_TYPE_TTD)
        .order_by("seq_tahapan", "id_tahapan")
        .values_list("pejabat_id", flat=True)
    )

    specimen_mode = _pick(tpl, setting, "specimen_mode", "upload")
    specimen_w_default = int(_pick(tpl, setting, "specimen_width", 300) or 300)
    specimen_h_default = int(_pick(tpl, setting, "specimen_height", 100) or 100)

    slots = []
    if tpl:
        slots = list(
            SuratTemplateSpecimenSlot.objects
            .filter(template=tpl, is_active=True)
            .order_by("urutan_signer")
        )

    num_pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    specimen_targets = []

    for idx, pid in enumerate(tte_steps, start=1):
        p = MstDataPegawai.objects.filter(id=pid).select_related("id_jabatan").first()
        if not p:
            continue

        slot = next((s for s in slots if int(s.urutan_signer or 0) == idx), None)

        slot_w = int(slot.width) if slot and slot.width else specimen_w_default
        slot_h = int(slot.height) if slot and slot.height else specimen_h_default

        # generated / upload
        png_bytes = None
        if specimen_mode == "generated":
            png_bytes = build_generated_specimen_for_pegawai(
                p,
                surat_template=tpl,
                width=slot_w,
                height=slot_h,
                logo_png_bytes=logo_bytes,
            )

        if not png_bytes:
            png_bytes = (
                _read_filefield_bytes(getattr(p, "specimen_ttd", None))
                or _read_filefield_bytes(getattr(p, "specimen_paraf", None))
            )

        if not png_bytes:
            continue

        if slot:
            target = _build_slot_target(
                pdf_bytes=pdf_bytes,
                num_pages=num_pages,
                slot=slot,
                default_w=specimen_w_default,
                default_h=specimen_h_default,
            )
        else:
            target = {
                "page": num_pages - 1,
                "x": 250 + ((idx - 1) * 20),
                "y": 80,
                "cover": None,
                "w": float(slot_w),
                "h": float(slot_h),
            }

        specimen_targets.append({
            "png": png_bytes,
            "target": target,
        })

    stamped_bytes = stamp_unsigned_pdf(
        pdf_bytes=pdf_bytes,
        qr_payload=qr_payload,
        marker_qr=marker_qr,
        marker_ttd=marker_ttd,
        qr_fallback=qr_fb,
        ttd_fallback=ttd_fb,
        qr_size=(qr_w, qr_h),
        ttd_size=(ttd_w, ttd_h),
        qr_offset=(0, 0),
        cover_marker=True,
        logo_png_bytes=logo_bytes,
        specimen_targets=specimen_targets,
        stamp_mode=stamp_mode,
        surat_template=tpl,
    )

    surat.file_surat_sha256 = sha256_bytes(pdf_bytes)
    surat.file_unsigned_sha256 = sha256_bytes(stamped_bytes)
    surat.stamp_last_at = timezone.now()
    surat.file_unsigned.save(
        f"surat_unsigned_{surat.id_surat}.pdf",
        ContentFile(stamped_bytes),
        save=False
    )
    surat.save()

    return {
        "surat_id": surat.id_surat,
        "tahapan_id": tahapan.id_tahapan,
        "qr_payload": qr_payload,
        "unsigned_path": getattr(surat.file_unsigned, "name", None),
        "stamped": True,
        "specimen_mode": specimen_mode,
        "specimen_count": len(specimen_targets),
        "note": "Stamped sekali: QR + semua specimen TTE saat paraf pertama.",
    }
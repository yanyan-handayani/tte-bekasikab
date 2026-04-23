import io
from typing import Optional, Tuple, Dict, Any
import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image


def find_text_occurrences_all(pdf_bytes: bytes, search_text: str):
    """
    Cari semua occurrence text di seluruh halaman.
    Return list:
      (page_index, x0, y0, w, h, page_w, page_h)
    """
    if not search_text:
        return []

    out = []
    needle = (search_text or "").strip()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=True,
            ) or []

            page_w = float(page.width)
            page_h = float(page.height)

            for w in words:
                txt = (w.get("text") or "").strip()
                if txt == needle:
                    x0 = float(w["x0"])
                    x1 = float(w["x1"])
                    top = float(w["top"])
                    bottom = float(w["bottom"])

                    y0 = page_h - bottom
                    y1 = page_h - top
                    bw = x1 - x0
                    bh = y1 - y0
                    out.append((pi, x0, y0, bw, bh, page_w, page_h))

    return out


def _pointer_targets(markers, *, w: float, h: float, mode: str = "below", offset=(0, 0)):
    out = []
    ox = float(offset[0] or 0)
    oy = float(offset[1] or 0)

    for (pi, mx, my, mw, mh, _, _) in markers:
        if mode == "below":
            x = mx + ox
            y = (my - h - 6) + oy
        elif mode == "above":
            x = mx + ox
            y = (my + mh + 6) + oy
        elif mode == "left":
            x = (mx - w - 6) + ox
            y = my + oy
        else:  # right
            x = (mx + mw + 6) + ox
            y = my + oy

        out.append({
            "page": pi,
            "x": x,
            "y": y,
            "cover": None,
            "w": w,
            "h": h,
        })
    return out


def page_bottom_strip_is_empty(pdf_bytes: bytes, page_index: int, *, strip_h: float = 90.0) -> bool:
    """
    True  => strip bawah kosong (tidak ada teks)
    False => ada teks di strip bawah
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if page_index < 0 or page_index >= len(pdf.pages):
            return True
        page = pdf.pages[page_index]
        page_h = float(page.height)
        # crop bagian bawah (origin pdfplumber: kiri-atas), bbox=(x0, top, x1, bottom)
        cropped = page.crop((0, page_h - strip_h, page.width, page_h))
        text = (cropped.extract_text() or "").strip()
        return len(text) == 0


def make_qr_with_center_logo(qr_payload: str, logo_png_bytes: Optional[bytes], *, size_px: int = 512) -> bytes:
    """
    Generate QR (PNG bytes). Jika logo_png_bytes diberikan, tempel di tengah QR.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # high karena pakai logo
        box_size=10,
        border=2,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    # resize ke size_px
    img = img.resize((size_px, size_px), Image.Resampling.LANCZOS)

    if logo_png_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")
            # ukuran logo 18% dari QR
            logo_size = int(size_px * 0.18)
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            # center
            x = (size_px - logo_size) // 2
            y = (size_px - logo_size) // 2

            # bikin background putih (opsional) biar logo keliatan
            pad = int(logo_size * 0.10)
            bg = Image.new("RGBA", (logo_size + pad * 2, logo_size + pad * 2), (255, 255, 255, 255))
            bg_x = (size_px - bg.width) // 2
            bg_y = (size_px - bg.height) // 2
            img.alpha_composite(bg, (bg_x, bg_y))

            img.alpha_composite(logo, (x, y))
        except Exception:
            # kalau logo gagal diproses, tetap return QR tanpa logo
            pass

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def find_text_marker(pdf_bytes: bytes, marker_text: str):
    """
    Cari 1 marker (first occurrence) di seluruh halaman.
    Return tuple:
      (page_index, x0, y0, w, h, page_w, page_h)
    Koordinat: origin kiri-bawah (PDF points).
    """
    if not marker_text:
        return None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
            ) or []

            # pdfplumber: x0,x1,top,bottom (origin kiri-atas)
            # konversi ke PDF coordinate (origin kiri-bawah):
            # y0 = page_h - bottom
            # y1 = page_h - top
            page_w = float(page.width)
            page_h = float(page.height)

            for w in words:
                txt = (w.get("text") or "")
                if txt == marker_text:
                    x0 = float(w["x0"])
                    x1 = float(w["x1"])
                    top = float(w["top"])
                    bottom = float(w["bottom"])

                    y0 = page_h - bottom
                    y1 = page_h - top
                    bw = (x1 - x0)
                    bh = (y1 - y0)
                    return (pi, x0, y0, bw, bh, page_w, page_h)

    return None


def find_text_markers_all(pdf_bytes: bytes, marker_text: str):
    """
    Cari semua marker occurrences di seluruh halaman.
    Return list of tuples:
      (page_index, x0, y0, w, h, page_w, page_h)
    """
    if not marker_text:
        return []

    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
            ) or []

            page_w = float(page.width)
            page_h = float(page.height)

            for w in words:
                txt = (w.get("text") or "")
                if txt == marker_text:
                    x0 = float(w["x0"])
                    x1 = float(w["x1"])
                    top = float(w["top"])
                    bottom = float(w["bottom"])

                    y0 = page_h - bottom
                    y1 = page_h - top
                    bw = (x1 - x0)
                    bh = (y1 - y0)
                    out.append((pi, x0, y0, bw, bh, page_w, page_h))

    return out


def resolve_page_index(page_spec: Any, num_pages: int) -> int:
    """
    page_spec:
      - "first" / "last"
      - int (0-index)
      - int (1-index) kalau dikirim >0? (kita treat 0-index; tapi aman clamp)
    """
    if num_pages <= 0:
        return 0

    if page_spec in (None, "", "last"):
        return num_pages - 1

    if page_spec == "first":
        return 0

    if isinstance(page_spec, int):
        # clamp
        if page_spec < 0:
            return 0
        if page_spec >= num_pages:
            return num_pages - 1
        return page_spec

    # string int?
    if isinstance(page_spec, str) and page_spec.isdigit():
        pi = int(page_spec)
        if pi < 0:
            return 0
        if pi >= num_pages:
            return num_pages - 1
        return pi

    return num_pages - 1


def _build_overlay(page_w: float, page_h: float, ops: list):
    """
    Buat overlay PDF page (pypdf) menggunakan reportlab.
    ops: list of callable(canvas)->None
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    for op in ops:
        op(c)
    c.save()
    buf.seek(0)
    overlay_reader = PdfReader(buf)
    return overlay_reader.pages[0]


def stamp_unsigned_pdf(
    *,
    pdf_bytes: bytes,
    qr_payload: str,
    marker_qr: str = "[QR]",
    marker_ttd: str = "[TTD{n}]",
    qr_fallback: Dict[str, Any] = None,
    ttd_fallback: Dict[str, Any] = None,
    qr_size: Tuple[float, float] = (110, 110),
    ttd_size: Tuple[float, float] = (120, 60),
    qr_offset: Tuple[float, float] = (0, 0),
    ttd_offset: Tuple[float, float] = (0, 0),
    cover_marker: bool = True,
    logo_png_bytes: Optional[bytes] = None,
    specimen_png_bytes: Optional[bytes] = None,
    specimen_png_list: Optional[list] = None,
    specimen_targets: Optional[list] = None,
    stamp_mode: str = "all_markers",
    surat_template: Any = None,
) -> bytes:
    def _tpl_get(key: str, default=None):
        if not surat_template:
            return default
        if isinstance(surat_template, dict):
            return surat_template.get(key, default)
        return getattr(surat_template, key, default)

    # override template untuk QR saja
    tpl_stamp_mode = _tpl_get("stamp_mode")
    if tpl_stamp_mode in ("marker", "all_markers"):
        stamp_mode = tpl_stamp_mode

    tpl_qr_marker = _tpl_get("qr_marker_text")
    if tpl_qr_marker:
        marker_qr = str(tpl_qr_marker)

    tpl_ttd_marker = _tpl_get("ttd_marker_text")
    if tpl_ttd_marker:
        marker_ttd = str(tpl_ttd_marker)

    tpl_qr_w = _tpl_get("qr_width")
    tpl_qr_h = _tpl_get("qr_height")
    if tpl_qr_w is not None or tpl_qr_h is not None:
        base_w, base_h = qr_size
        qr_size = (
            float(tpl_qr_w) if tpl_qr_w is not None else float(base_w),
            float(tpl_qr_h) if tpl_qr_h is not None else float(base_h),
        )

    tpl_ttd_w = _tpl_get("ttd_width")
    tpl_ttd_h = _tpl_get("ttd_height")
    if tpl_ttd_w is not None or tpl_ttd_h is not None:
        base_w, base_h = ttd_size
        ttd_size = (
            float(tpl_ttd_w) if tpl_ttd_w is not None else float(base_w),
            float(tpl_ttd_h) if tpl_ttd_h is not None else float(base_h),
        )

    qr_w, qr_h = float(qr_size[0]), float(qr_size[1])

    qr_fallback = qr_fallback or {
        "page": "last",
        "x": 450,
        "y": 80,
        "w": qr_w,
        "h": qr_h,
    }

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    num_pages = len(reader.pages)

    qr_png = make_qr_with_center_logo(qr_payload, logo_png_bytes, size_px=512)

    def _sort_lr_tb(markers):
        return sorted(markers, key=lambda m: (m[0], -m[2], m[1]))

    def _marker_targets(markers, *, w: float, h: float, offset: Tuple[float, float]):
        out = []
        for (pi, mx, my, mw, mh, _, _) in markers:
            marker_cx = mx + (mw / 2.0)
            marker_cy = my + (mh / 2.0)
            x = marker_cx - (w / 2.0) + float(offset[0])
            y = marker_cy - (h / 2.0) + float(offset[1])
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

    def _get_marks(marker_text: str):
        marks = find_text_markers_all(pdf_bytes, marker_text)
        marks = _sort_lr_tb([m for m in marks if m])
        return marks

    # -------------------------
    # QR targets
    # -------------------------
    qr_marks = _get_marks(marker_qr)
    if qr_marks:
        qr_targets = _marker_targets(qr_marks, w=qr_w, h=qr_h, offset=qr_offset)
    else:
        qr_page_index = resolve_page_index(qr_fallback.get("page", "last"), num_pages)
        qr_targets = [{
            "page": qr_page_index,
            "x": float(qr_fallback["x"]),
            "y": float(qr_fallback["y"]),
            "cover": None,
            "w": float(qr_fallback.get("w", qr_w)),
            "h": float(qr_fallback.get("h", qr_h)),
        }]

    specimen_targets = specimen_targets or []

    # -------------------------
    # Merge overlays
    # -------------------------
    for page_index, page in enumerate(reader.pages):
        page_w = float(page.mediabox.width)
        page_h = float(page.mediabox.height)
        ops = []

        # QR
        for tgt in qr_targets:
            if tgt["page"] != page_index:
                continue

            w = float(tgt.get("w", qr_w))
            h = float(tgt.get("h", qr_h))

            if cover_marker and tgt.get("cover"):
                cx, cy, rw, rh = tgt["cover"]

                def cover_op(c, x=cx, y=cy, rw=rw, rh=rh):
                    c.setFillColorRGB(1, 1, 1)
                    c.rect(x, y, rw, rh, fill=1, stroke=0)

                ops.append(cover_op)

            def draw_qr(c, x=float(tgt["x"]), y=float(tgt["y"]), w=w, h=h, img=qr_png):
                c.drawImage(ImageReader(io.BytesIO(img)), x, y, width=w, height=h, mask="auto")

            ops.append(draw_qr)

        # Specimen explicit dari service
        for item in specimen_targets:
            tgt = item["target"]
            img = item["png"]

            if tgt["page"] != page_index:
                continue

            w = float(tgt["w"])
            h = float(tgt["h"])

            if cover_marker and tgt.get("cover"):
                cx, cy, rw, rh = tgt["cover"]

                def cover_spec(c, x=cx, y=cy, rw=rw, rh=rh):
                    c.setFillColorRGB(1, 1, 1)
                    c.rect(x, y, rw, rh, fill=1, stroke=0)

                ops.append(cover_spec)

            def draw_spec(c, x=float(tgt["x"]), y=float(tgt["y"]), w=w, h=h, img=img):
                c.drawImage(ImageReader(io.BytesIO(img)), x, y, width=w, height=h, mask="auto")

            ops.append(draw_spec)

        if ops:
            overlay = _build_overlay(page_w, page_h, ops)
            page.merge_page(overlay)

        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def build_bsre_footnote_center_op(
    *,
    page_w: float,
    y: float,
    text_lines: list[str],
    font_name: str = "Helvetica",
    font_size: int = 8,
    line_gap: int = 10,
    logo_png_bytes: Optional[bytes] = None,
    logo_w: float = 45,
    logo_h: float = 45,
    gap_logo_text: float = 10,
    x_padding: float = 20,
):
    """
    Footnote tengah bawah.
    """
    def _op(c: canvas.Canvas):
        x = x_padding

        # logo kiri
        if logo_png_bytes:
            try:
                c.drawImage(
                    ImageReader(io.BytesIO(logo_png_bytes)),
                    x, y,
                    width=logo_w, height=logo_h,
                    mask="auto",
                )
                x += logo_w + gap_logo_text
            except Exception:
                pass

        # text center-ish (tetap mulai setelah logo)
        c.setFont(font_name, font_size)
        ty = y + (logo_h - font_size)  # kira-kira align
        for i, line in enumerate(text_lines):
            c.drawString(x, ty - (i * line_gap), line)

    return _op


def stamp_bsre_footnote_each_page_if_empty(
    *,
    pdf_bytes: bytes,
    text_lines: Optional[list[str]] = None,
    footnote_text: Optional[str] = None,
    y: float = 20,
    strip_h: float = 90,
    logo_png_bytes: Optional[bytes] = None,
    bsre_logo_png_bytes: Optional[bytes] = None,  # <- tambahkan ini
) -> bytes:
    """
    Stamp catatan BSrE di bagian bawah setiap halaman, 
    tapi hanya jika strip bawah kosong.

    Kompat:
    - text_lines: list[str]
    - footnote_text: str
    - logo_png_bytes
    - bsre_logo_png_bytes (alias)
    """

    # 🔹 Samakan logo param (prioritaskan bsre_logo_png_bytes jika ada)
    if bsre_logo_png_bytes is not None:
        logo_png_bytes = bsre_logo_png_bytes

    # 🔹 Kompat text param
    if text_lines is None:
        if footnote_text is None:
            text_lines = []
        else:
            text_lines = [
                ln.strip()
                for ln in str(footnote_text).splitlines()
                if ln.strip()
            ]

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        page_w = float(page.mediabox.width)
        page_h = float(page.mediabox.height)

        if text_lines and page_bottom_strip_is_empty(pdf_bytes, i, strip_h=strip_h):
            op = build_bsre_footnote_center_op(
                page_w=page_w,
                y=y,
                text_lines=text_lines,
                logo_png_bytes=logo_png_bytes,
            )
            overlay = _build_overlay(page_w, page_h, [op])
            page.merge_page(overlay)

        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


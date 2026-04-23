import io
from typing import Optional, Tuple, Dict, Any
import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image


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
    stamp_mode: str = "all_markers",  # "marker" / "all_markers"

    # inject SuratTemplate (object model Django atau dict)
    # key yang dibaca:
    # - qr_marker_text, qr_width, qr_height, qr_x, qr_y
    # - ttd_marker_text, ttd_width, ttd_height
    # - stamp_mode (optional)
    surat_template: Any = None,
) -> bytes:
    """
    STAMP UNSIGNED PDF:
    - QR: stamp berdasarkan marker_qr (1 atau semua marker tergantung stamp_mode), fallback jika tidak ada marker.
    - Specimen (TTD/Paraf): bisa banyak signer.
      * Slot mode: marker_ttd mengandung "{n}" -> cari [TTD1],[TTD2],...
         - kalau TTD1/TTD2 tidak ditemukan -> fallback ke marker generik [TTD] (urut kiri->kanan)
         - kalau [TTD] juga tidak ada -> fallback koordinat split-box:
              x1=center box1, x2=center box2, ...; y ambil dari ttd_fallback['y']
      * Generic mode: marker_ttd tanpa "{n}" -> pakai marker itu; jika tidak ada -> split-box fallback.

    Template override:
    - QR:
      * marker_qr dari surat_template.qr_marker_text (kalau ada)
      * qr_size dari surat_template.qr_width/qr_height (kalau ada)
      * qr_fallback x/y dari surat_template.qr_x/qr_y (kalau ada)
    - TTD:
      * marker_ttd dari surat_template.ttd_marker_text (kalau ada)
      * ttd_size dari surat_template.ttd_width/ttd_height (kalau ada)
    - stamp_mode:
      * override dari surat_template.stamp_mode (kalau ada)
    """

    # -------------------------
    # SuratTemplate overrides (minimal, keep old marker detection behavior)
    # Priority: surat_template > defaults passed to function
    # -------------------------

    def _tpl_get(key: str, default=None):
        if not surat_template:
            return default
        if isinstance(surat_template, dict):
            return surat_template.get(key, default)
        return getattr(surat_template, key, default)

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

    # -------------------------
    # 0) Apply SuratTemplate overrides
    # -------------------------
    def _tpl_get(key: str, default=None):
        if not surat_template:
            return default
        if isinstance(surat_template, dict):
            return surat_template.get(key, default)
        return getattr(surat_template, key, default)

    # tpl_stamp_mode = _tpl_get("stamp_mode")
    # if tpl_stamp_mode in ("marker", "all_markers"):
    #     stamp_mode = tpl_stamp_mode
    stamp_mode = "all_markers"

    # QR overrides
    tpl_qr_marker = _tpl_get("qr_marker_text")
    if tpl_qr_marker:
        marker_qr = str(tpl_qr_marker)

    tpl_qr_w = _tpl_get("qr_width")
    tpl_qr_h = _tpl_get("qr_height")
    if tpl_qr_w is not None or tpl_qr_h is not None:
        base_w, base_h = qr_size
        qr_size = (
            float(tpl_qr_w) if tpl_qr_w is not None else float(base_w),
            float(tpl_qr_h) if tpl_qr_h is not None else float(base_h),
        )

    tpl_qr_x = _tpl_get("qr_x")
    tpl_qr_y = _tpl_get("qr_y")

    # TTD overrides (marker + size saja)
    tpl_ttd_marker = _tpl_get("ttd_marker_text")
    if tpl_ttd_marker:
        marker_ttd = str(tpl_ttd_marker)

    tpl_ttd_w = _tpl_get("ttd_width")
    tpl_ttd_h = _tpl_get("ttd_height")
    if tpl_ttd_w is not None or tpl_ttd_h is not None:
        base_w, base_h = ttd_size
        ttd_size = (
            float(tpl_ttd_w) if tpl_ttd_w is not None else float(base_w),
            float(tpl_ttd_h) if tpl_ttd_h is not None else float(base_h),
        )

    # ---- fallback defaults ----
    qr_w, qr_h = float(qr_size[0]), float(qr_size[1])
    spec_w, spec_h = float(ttd_size[0]), float(ttd_size[1])

    qr_fallback = qr_fallback or {"page": "last", "x": 450, "y": 80, "w": qr_w, "h": qr_h}
    ttd_fallback = ttd_fallback or {"page": "last", "x": 320, "y": 80, "w": spec_w, "h": spec_h}

    qr_fallback = dict(qr_fallback)
    qr_fallback.setdefault("w", qr_w)
    qr_fallback.setdefault("h", qr_h)
    qr_fallback["w"] = float(qr_fallback.get("w", qr_w))
    qr_fallback["h"] = float(qr_fallback.get("h", qr_h))

    ttd_fallback = dict(ttd_fallback)
    ttd_fallback.setdefault("w", spec_w)
    ttd_fallback.setdefault("h", spec_h)
    ttd_fallback["w"] = float(ttd_fallback.get("w", spec_w))
    ttd_fallback["h"] = float(ttd_fallback.get("h", spec_h))

    # template override fallback QR x/y (PRIORITAS)
    if tpl_qr_x is not None:
        qr_fallback["x"] = float(tpl_qr_x)
    if tpl_qr_y is not None:
        qr_fallback["y"] = float(tpl_qr_y)

    # -------------------------
    # 1) Read PDF & prepare assets
    # -------------------------
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    num_pages = len(reader.pages)

    qr_png = make_qr_with_center_logo(qr_payload, logo_png_bytes, size_px=512)

    specimens: list[bytes] = []
    if specimen_png_list:
        specimens = [b for b in specimen_png_list if b]
    elif specimen_png_bytes:
        specimens = [specimen_png_bytes]

    def _sort_lr_tb(markers):
        # page asc, y desc (top->bottom), x asc (left->right)
        return sorted(markers, key=lambda m: (m[0], -m[2], m[1]))

    def _marker_targets(markers, *, w: float, h: float, offset: Tuple[float, float]):
        out = []
        for (pi, mx, my, mw, mh, _, _) in markers:
            marker_cx = mx + (mw / 2.0)
            marker_cy = my + (mh / 2.0)
            x = marker_cx - (w / 2.0) + float(offset[0])
            y = marker_cy - (h / 2.0) + float(offset[1])
            cover = (mx, my, mw, mh) if cover_marker else None
            out.append({"page": pi, "x": x, "y": y, "cover": cover})
        return out

    def _get_marks(marker_text: str):
        if stamp_mode == "all_markers":
            marks = find_text_markers_all(pdf_bytes, marker_text)
            marks = _sort_lr_tb([m for m in marks if m])
            return marks
        one = find_text_marker(pdf_bytes, marker_text)
        return [one] if one else []

    # -------------------------
    # 2) QR targets
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

    # -------------------------
    # 3) Specimen targets (multi)
    # -------------------------
    spec_targets_per_specimen: list[list[dict]] = []

    def _fallback_split_boxes_for_specimens() -> list[list[dict]]:
        """
        Fallback TTD saat TIDAK ada marker sama sekali.
        - Kalau n>1: bagi lebar halaman menjadi n box, x_i = center(box_i) - (w/2)
        - y ambil dari ttd_fallback['y'] (setting)
        - page ambil dari ttd_fallback['page']
        """
        n = len(specimens)
        if n <= 0:
            return []

        spec_page_index = resolve_page_index(ttd_fallback.get("page", "last"), num_pages)
        page_w = float(reader.pages[spec_page_index].mediabox.width)

        y = float(ttd_fallback["y"])
        w0 = float(ttd_fallback.get("w", spec_w))
        h0 = float(ttd_fallback.get("h", spec_h))

        if n == 1:
            return [[{
                "page": spec_page_index,
                "x": float(ttd_fallback["x"]),
                "y": y,
                "cover": None,
                "w": w0,
                "h": h0,
            }]]

        box_w = page_w / float(n)
        out: list[list[dict]] = []
        for i in range(n):
            center_x = (box_w * i) + (box_w / 2.0)
            x_i = center_x - (w0 / 2.0)
            out.append([{
                "page": spec_page_index,
                "x": x_i,
                "y": y,
                "cover": None,
                "w": w0,
                "h": h0,
            }])
        return out

    if specimens:
        if "{n}" in marker_ttd:
            # slot mode: [TTD1],[TTD2],...
            slot_targets_tmp: list[list[dict]] = []
            slot_found_any = False

            for idx in range(1, len(specimens) + 1):
                mk = marker_ttd.format(n=idx)
                marks = _get_marks(mk)
                if marks:
                    slot_found_any = True
                    slot_targets_tmp.append(_marker_targets(marks, w=spec_w, h=spec_h, offset=ttd_offset))
                else:
                    slot_targets_tmp.append([])

            if slot_found_any:
                spec_targets_per_specimen = slot_targets_tmp
            else:
                # fallback to generic [TTD]
                generic_marks = _get_marks("[TTD]")
                if generic_marks:
                    spec_targets_per_specimen = []
                    for i in range(len(specimens)):
                        if i < len(generic_marks):
                            spec_targets_per_specimen.append(
                                _marker_targets([generic_marks[i]], w=spec_w, h=spec_h, offset=ttd_offset)
                            )
                        else:
                            spec_targets_per_specimen.append([])
                else:
                    # fallback: split boxes
                    spec_targets_per_specimen = _fallback_split_boxes_for_specimens()

        else:
            # generic marker mode (tanpa {n})
            marks = _get_marks(marker_ttd)
            if marks:
                if stamp_mode == "all_markers":
                    spec_targets_per_specimen = []
                    for i in range(len(specimens)):
                        if i < len(marks):
                            spec_targets_per_specimen.append(
                                _marker_targets([marks[i]], w=spec_w, h=spec_h, offset=ttd_offset)
                            )
                        else:
                            spec_targets_per_specimen.append([])
                else:
                    # only one marker -> only place first specimen (avoid overwrite)
                    spec_targets_per_specimen = [_marker_targets(marks[:1], w=spec_w, h=spec_h, offset=ttd_offset)] + \
                                               [[] for _ in range(len(specimens) - 1)]
            else:
                # fallback: split boxes
                spec_targets_per_specimen = _fallback_split_boxes_for_specimens()

    # -------------------------
    # 4) Merge overlays per page
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

        # Specimens
        if specimens and spec_targets_per_specimen:
            for si, spec in enumerate(specimens):
                if si >= len(spec_targets_per_specimen):
                    break
                for tgt in spec_targets_per_specimen[si]:
                    if tgt["page"] != page_index:
                        continue

                    w = float(tgt.get("w", spec_w))
                    h = float(tgt.get("h", spec_h))

                    if cover_marker and tgt.get("cover"):
                        cx, cy, rw, rh = tgt["cover"]

                        def cover2(c, x=cx, y=cy, rw=rw, rh=rh):
                            c.setFillColorRGB(1, 1, 1)
                            c.rect(x, y, rw, rh, fill=1, stroke=0)

                        ops.append(cover2)

                    def draw_spec(c, x=float(tgt["x"]), y=float(tgt["y"]), w=w, h=h, img=spec):
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


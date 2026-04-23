import io
from pathlib import Path
from typing import Optional, List

from PIL import Image, ImageDraw, ImageFont


PANGKAT_BY_GOLONGAN = {
    "i/a": "Juru muda",
    "i/b": "Juru muda Tk. I",
    "i/c": "Juru",
    "i/d": "Juru Tk. I",
    "ii/a": "Pengatur muda",
    "ii/b": "Pengatur muda Tk. I",
    "ii/c": "Pengatur",
    "ii/d": "Pengatur Tk. I",
    "iii/a": "Penata muda",
    "iii/b": "Penata muda Tk. I",
    "iii/c": "Penata",
    "iii/d": "Penata Tk. I",
    "iv/a": "Pembina",
    "iv/b": "Pembina Tk I",
    "iv/c": "Pembina utama muda",
    "iv/d": "Pembina utama madya",
    "iv/e": "Pembina utama",
}


def normalize_golongan(gol):
    return (gol or "").strip().lower()


def resolve_pangkat_from_golongan(golongan: str) -> str:
    gol = normalize_golongan(golongan)
    if not gol:
        return ""
    pangkat = PANGKAT_BY_GOLONGAN.get(gol)
    if pangkat:
        return f"{pangkat} ({golongan})"
    return f"Golongan {golongan}"


def _load_font(font_size: int, bold: bool = False):
    font_size = max(7, int(font_size))

    if bold:
        candidates = [
            "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, font_size)
            except Exception:
                pass

    return ImageFont.load_default()


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font):
    return draw.textbbox((0, 0), text or "Ag", font=font)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = _text_bbox(draw, text, font)
    return int(b[2] - b[0])


def _text_height(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = _text_bbox(draw, text, font)
    return int(b[3] - b[1])


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        trial = f"{current} {word}"
        if _text_width(draw, trial, font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def _fit_font(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    *,
    start_size: int,
    min_size: int,
    max_width: int,
    bold: bool = False,
):
    size = max(min_size, start_size)
    lines = lines or ["-"]

    while size >= min_size:
        font = _load_font(size, bold=bold)
        widest = max(_text_width(draw, line, font) for line in lines)
        if widest <= max_width:
            return font
        size -= 1

    return _load_font(min_size, bold=bold)


def _shorten_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    text = (text or "").strip()
    if not text:
        return "-"

    if _text_width(draw, text, font) <= max_width:
        return text

    s = text
    while s:
        candidate = s.rstrip(" .,") + "..."
        if _text_width(draw, candidate, font) <= max_width:
            return candidate
        s = s[:-1]

    return "..."


def _draw_underlined_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill="black"):
    draw.text((x, y), text, fill=fill, font=font)
    bbox = draw.textbbox((x, y), text, font=font)
    underline_y = bbox[3] + 1
    draw.line((bbox[0], underline_y, bbox[2], underline_y), fill=fill, width=1)


def generate_specimen_png(
    *,
    nama: str,
    jabatan: str,
    pangkat: str,
    logo_png_bytes: Optional[bytes] = None,
    width: int = 240,
    height: int = 120,
    bg_color: str = "#ffffff",
    border_color: str = "#000000",
) -> bytes:
    width = max(190, int(width))
    height = max(85, int(height))

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    border_w = 2
    draw.rectangle([0, 0, width - 1, height - 1], outline=border_color, width=border_w)

    scale_x = width / 320.0
    scale_y = height / 125.0
    scale = min(scale_x, scale_y)

    pad_x = max(6, int(7 * scale))
    pad_y = max(5, int(6 * scale))

    inner_w = width - (pad_x * 2)
    inner_h = height - (pad_y * 2)

    logo_area_w = max(56, int(84 * scale))
    gap = max(6, int(8 * scale))

    text_x = pad_x + logo_area_w + gap
    text_y = pad_y + max(0, int(2 * scale))
    text_w = max(50, width - text_x - pad_x)
    text_h = max(20, height - text_y - pad_y)

    intro_size = max(6, int(8 * scale))
    jabatan_size = max(7, int(9 * scale))
    nama_size = max(7, int(10 * scale))
    pangkat_size = max(6, int(8 * scale))

    font_intro = _load_font(intro_size, bold=False)

    intro_text = "Ditandatangani secara elektronik oleh:"

    jabatan_text = (jabatan or "").strip().upper() or "-"
    preview_jabatan_font = _load_font(jabatan_size, bold=False)
    jabatan_lines = _wrap_text(draw, jabatan_text, preview_jabatan_font, text_w)
    jabatan_lines = jabatan_lines[:3] if jabatan_lines else ["-"]

    font_jabatan = _fit_font(
        draw,
        jabatan_lines,
        start_size=jabatan_size,
        min_size=max(6, int(7 * scale)),
        max_width=text_w,
        bold=False,
    )

    jabatan_lines = _wrap_text(draw, jabatan_text, font_jabatan, text_w)
    if len(jabatan_lines) > 3:
        jabatan_lines = jabatan_lines[:3]
        jabatan_lines[-1] = _shorten_to_width(draw, jabatan_lines[-1], font_jabatan, text_w)

    nama_text = (nama or "").strip().upper() or "-"
    font_nama = _load_font(nama_size, bold=True)
    nama_text = _shorten_to_width(draw, nama_text, font_nama, text_w)

    pangkat_text = (pangkat or "").strip() or "-"
    font_pangkat = _load_font(pangkat_size, bold=False)
    pangkat_text = _shorten_to_width(draw, pangkat_text, font_pangkat, text_w)

    intro_h = _text_height(draw, "Ag", font_intro)
    jabatan_h = _text_height(draw, "Ag", font_jabatan)
    nama_h = _text_height(draw, "Ag", font_nama)
    pangkat_h = _text_height(draw, "Ag", font_pangkat)

    gap_after_intro = max(1, int(1 * scale))
    gap_jabatan = 0
    gap_before_nama = max(1, int(3 * scale))
    gap_before_pangkat = 0

    total_text_h = (
        intro_h
        + gap_after_intro
        + (len(jabatan_lines) * jabatan_h)
        + gap_before_nama
        + nama_h
        + gap_before_pangkat
        + pangkat_h
    )

    y = text_y + max(0, (text_h - total_text_h) // 2)

    if logo_png_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")
            target_w = max(40, int(58 * scale))
            target_h = max(52, int(72 * scale))
            logo.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

            lx = pad_x + max(0, (logo_area_w - logo.width) // 2)
            ly = pad_y + max(0, (inner_h - logo.height) // 2)
            img.alpha_composite(logo, (lx, ly))
        except Exception:
            pass

    draw.text((text_x, y), intro_text, fill="black", font=font_intro)
    y += intro_h + gap_after_intro

    for line in jabatan_lines:
        draw.text((text_x, y), line, fill="black", font=font_jabatan)
        y += jabatan_h + gap_jabatan

    y += gap_before_nama
    _draw_underlined_text(draw, text_x, y, nama_text, font_nama, fill="black")
    y += nama_h + gap_before_pangkat

    draw.text((text_x, y), pangkat_text, fill="black", font=font_pangkat)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def build_generated_specimen_for_pegawai(
    pegawai,
    *,
    surat_template=None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    logo_png_bytes: Optional[bytes] = None,
) -> bytes:
    nama = (getattr(pegawai, "nama_lengkap", "") or "").strip()

    jabatan = ""
    if getattr(pegawai, "id_jabatan", None):
        jabatan = str(pegawai.id_jabatan).strip()

    gol = (getattr(pegawai, "golongan", "") or "").strip()
    pangkat = resolve_pangkat_from_golongan(gol) if gol else ""

    final_width = 320
    final_height = 125
    bg_color = "#ffffff"
    border_color = "#000000"

    if surat_template is not None:
        final_width = int(getattr(surat_template, "specimen_width", None) or final_width)
        final_height = int(getattr(surat_template, "specimen_height", None) or final_height)
        bg_color = getattr(surat_template, "specimen_bg_color", None) or bg_color
        border_color = getattr(surat_template, "specimen_border_color", None) or border_color

    if width:
        final_width = int(width)
    if height:
        final_height = int(height)

    return generate_specimen_png(
        nama=nama,
        jabatan=jabatan,
        pangkat=pangkat,
        logo_png_bytes=logo_png_bytes,
        width=final_width,
        height=final_height,
        bg_color=bg_color,
        border_color=border_color,
    )
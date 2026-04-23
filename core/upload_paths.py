import os
import uuid
from django.utils import timezone


def surat_pdf_upload_to(instance, filename: str) -> str:
    """
    surat/YYYY/MM/DD/<uuid>.pdf
    """
    dt = timezone.localdate()
    _, ext = os.path.splitext(filename)
    ext = (ext or "").lower()

    # paksa .pdf (kalau user upload PDF tapi ekstensi aneh)
    if ext != ".pdf":
        ext = ".pdf"

    return f"surat/{dt:%Y/%m/%d}/{uuid.uuid4().hex}{ext}"

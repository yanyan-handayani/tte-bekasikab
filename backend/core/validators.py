from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

pdf_extension_validator = FileExtensionValidator(allowed_extensions=["pdf"])


def validate_pdf_magic(file_obj):
    """
    Cek cepat magic header %PDF.
    Ekstensi bisa dipalsukan, jadi ini lebih aman.
    """
    if not file_obj:
        return

    pos = file_obj.tell()
    try:
        file_obj.seek(0)
        header = file_obj.read(4)
        if header != b"%PDF":
            raise ValidationError("File bukan PDF yang valid.")
    finally:
        file_obj.seek(pos)


def validate_max_10mb(file_obj):
    if file_obj.size > 10 * 1024 * 1024:
        raise ValidationError("Maksimal ukuran file 10MB.")
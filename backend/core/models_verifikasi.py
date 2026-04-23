# core/models_verifikasi.py
import secrets
from django.db import models
from django.utils import timezone

class SuratVerifikasi(models.Model):
    """
    Mapping token verifikasi (QR) -> surat.
    Token panjang seperti: QyUZNJNW45Ydui8s4ZuPGEF3DumWZwD80woWmm4BUbw
    """
    id = models.BigAutoField(primary_key=True)

    token = models.CharField(max_length=128, unique=True, db_index=True)

    surat = models.ForeignKey(
        "core.Surat",
        db_column="id_surat",
        on_delete=models.CASCADE,
        related_name="verifikasi_set",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_access_at = models.DateTimeField(null=True, blank=True)
    hit_count = models.PositiveIntegerField(default=0)

    @staticmethod
    def new_token() -> str:
        # URL-safe, panjang, mirip contoh token abang
        return secrets.token_urlsafe(32)

    class Meta:
        db_table = "surat_verifikasi"
        verbose_name = "Surat Verifikasi"
        verbose_name_plural = "Surat Verifikasi"
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.fields import EncryptedTextField
from django.utils import timezone


class User(AbstractUser):
    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        db_column="pegawai_ref_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    instansi = models.ForeignKey(
        "core.RefInstansi",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="instansi_id",
        related_name="admin_users",
    )

    full_name = models.CharField(max_length=255, null=True, blank=True)

    # legacy SHA1 pin (40 hex)
    legacy_pin_hash = models.CharField(max_length=40, null=True, blank=True)

    failed_login_count = models.PositiveSmallIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    # === 2FA ===
    twofa_enabled = models.BooleanField(default=False)
    twofa_secret = EncryptedTextField(null=True, blank=True)
    twofa_backup_codes = EncryptedTextField(null=True, blank=True)
    username_hash = models.CharField(max_length=64, null=True, blank=True, unique=True, db_index=True)

    # === password policy ===
    password_changed_at = models.DateTimeField(default=timezone.now)
    must_change_password = models.BooleanField(default=False)
    password_expires_in_days = 90

    def is_locked_out(self) -> bool:
        return bool(self.lockout_until and self.lockout_until > timezone.now())

    def register_failed_login(self, max_attempts=3, lock_minutes=15):
        now = timezone.now()
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.lockout_until = now + timezone.timedelta(minutes=lock_minutes)
        self.save(update_fields=["failed_login_count", "lockout_until"])

    def register_success_login(self):
        self.failed_login_count = 0
        self.lockout_until = None
        self.save(update_fields=["failed_login_count", "lockout_until"])

    def password_is_expired(self) -> bool:
        if not self.password_changed_at:
            return True
        return self.password_changed_at <= (
            timezone.now() - timezone.timedelta(days=self.password_expires_in_days)
        )

    def mark_password_changed(self):
        self.password_changed_at = timezone.now()
        self.must_change_password = False

    def set_password_and_update_expiry(self, raw_password: str):
        super().set_password(raw_password)
        self.mark_password_changed()

    def __str__(self):
        return self.username


class EmailSendLog(models.Model):
    class Purpose(models.TextChoices):
        PASSWORD_RESET = "password_reset", "Password Reset"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"  # misal user ada tapi gak ada email target

    id = models.BigAutoField(primary_key=True)
    purpose = models.CharField(max_length=50, choices=Purpose.choices)
    status = models.CharField(max_length=10, choices=Status.choices)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="email_logs",
    )

    to_email = models.EmailField(max_length=254, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)

    # jangan simpan token/reset_link mentah; cukup simpan info ringkas + error
    error_message = models.TextField(null=True, blank=True)

    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_send_log"
        verbose_name = "Email Send Log"
        verbose_name_plural = "Email Send Logs"

    def __str__(self):
        return f"{self.purpose} {self.status} to={self.to_email or '-'}"
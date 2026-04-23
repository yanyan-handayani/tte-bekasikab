import hashlib
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import User, EmailSendLog


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_hex_with_pepper(s: str) -> str:
    pepper = getattr(settings, "NIP_HASH_PEPPER", None) or getattr(settings, "PDP_ENC_KEY", None) or ""
    raw = f"{pepper}{s}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    model = User
    autocomplete_fields = ("pegawai", "instansi")

    list_display = (
        "username",
        "full_name",
        "instansi",
        "pegawai",
        "is_staff",
        "is_active",
        "twofa_enabled",
        "failed_login_count",
        "lockout_until",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "twofa_enabled", "instansi")

    search_fields = (
        "username",
        "full_name",
        "instansi__nama",
        "pegawai__nama_lengkap",
        "pegawai__nip_hash",
        "pegawai__nik_hash",
    )

    fieldsets = DjangoUserAdmin.fieldsets + (
        (_("Profil"), {"fields": ("full_name", "pegawai", "instansi")}),
        (_("2FA"), {"fields": ("twofa_enabled", "twofa_secret", "twofa_backup_codes")}),
        (_("Security / Lockout"), {
            "fields": (
                "failed_login_count",
                "lockout_until",
                "username_hash",
                "legacy_pin_hash",
                "password_changed_at",
                "must_change_password",
                "reset_lock_button",
            )
        }),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (_("Profil"), {"fields": ("full_name", "pegawai", "instansi")}),
        (_("2FA"), {"fields": ("twofa_enabled",)}),
    )

    readonly_fields = (
        "legacy_pin_hash",
        "username_hash",
        "twofa_secret",
        "twofa_backup_codes",
        "failed_login_count",
        "lockout_until",
        "last_login",
        "date_joined",
        "password_changed_at",
        "password_expires_in_days",
        "reset_lock_button",
    )

    actions = ("action_reset_lockout",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("pegawai", "instansi")

    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)
        term = (search_term or "").strip()

        if term.isdigit() and len(term) >= 10:
            h1 = sha256_hex(term)
            h2 = sha256_hex_with_pepper(term)

            qs = qs | queryset.filter(pegawai__nip_hash=h1) | queryset.filter(pegawai__nik_hash=h1)
            qs = qs | queryset.filter(pegawai__nip_hash=h2) | queryset.filter(pegawai__nik_hash=h2)
            use_distinct = True

        return qs, use_distinct

    @admin.action(description="Reset lock user terpilih")
    def action_reset_lockout(self, request, queryset):
        updated = queryset.update(failed_login_count=0, lockout_until=None)
        self.message_user(
            request,
            f"{updated} user berhasil di-reset lockout.",
            level=messages.SUCCESS,
        )

    def reset_lock_button(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse("admin:accounts_user_reset_lock", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" onclick="return confirm(\'Reset lock user ini?\')">Reset Lock User</a>',
            url
        )
    reset_lock_button.short_description = "Aksi Reset"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/reset-lock/",
                self.admin_site.admin_view(self.reset_lock_view),
                name="accounts_user_reset_lock",
            ),
        ]
        return custom_urls + urls

    def reset_lock_view(self, request, object_id, *args, **kwargs):
        obj = self.get_object(request, object_id)
        if obj is None:
            self.message_user(request, "User tidak ditemukan.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

        obj.failed_login_count = 0
        obj.lockout_until = None
        obj.save(update_fields=["failed_login_count", "lockout_until"])

        self.message_user(
            request,
            f"Lock user '{obj.username}' berhasil di-reset.",
            level=messages.SUCCESS,
        )

        return HttpResponseRedirect(
            reverse("admin:accounts_user_change", args=[obj.pk])
        )

@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = (
        "to_email",
        "created_at",
        "purpose",
        "status",
        "user",
        "subject",
    )

    search_fields = (
        "to_email",
        "subject",
        "error_message",
        "user__username",
        "user__full_name",
        "user__email",
    )

    list_filter = (
        "purpose",
        "status",
        "created_at",
    )

    ordering = ("-created_at",)
    list_per_page = 50
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
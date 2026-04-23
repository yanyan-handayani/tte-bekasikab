from django.contrib import admin
from . import models
from core.crypto import hash_lookup
from .forms import MstDataPegawaiAdminForm
from .admin_utils import mask_mid
from django.db import connection
from django.conf import settings
from django.utils.html import format_html
from core.utils.utils import get_instansi_scope_ids
from mptt.admin import DraggableMPTTAdmin
from django import forms
from django.forms import TextInput
from django.forms.models import BaseInlineFormSet

class TaJabatanInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)

        request = getattr(self, "request", None)
        if request:
            obj.created_by = request.user.username
            obj.updated_by = request.user.username

        if commit:
            obj.save()

        return obj

    def save_existing(self, form, instance, commit=True):
        obj = super().save_existing(form, instance, commit=False)

        request = getattr(self, "request", None)
        if request:
            obj.updated_by = request.user.username

        if commit:
            obj.save()

        return obj

class TaJabatanInlineForm(forms.ModelForm):
    class Meta:
        model = models.TaJabatan
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        parent_obj = kwargs.pop("parent_obj", None)
        super().__init__(*args, **kwargs)

        if "id_jabatan" not in self.fields:
            return

        qs = models.MstJabatan.objects.all()

        # scope normal
        scoped_qs = qs
        if parent_obj and getattr(parent_obj, "id_instansi_id", None):
            if request and not request.user.is_superuser:
                scope_ids = get_instansi_scope_ids(parent_obj.id_instansi_id)
                scoped_qs = qs.filter(instansi_id__in=scope_ids)

        # PENTING:
        # jika ada nilai existing / nilai terpilih, pastikan tetap ikut queryset
        selected_id = None

        # edit existing row
        if getattr(self.instance, "id_jabatan_id", None):
            selected_id = self.instance.id_jabatan_id

        # add row baru saat POST
        bound_val = self.data.get(self.add_prefix("id_jabatan"))
        if bound_val:
            try:
                selected_id = int(bound_val)
            except Exception:
                pass

        if selected_id:
            self.fields["id_jabatan"].queryset = (scoped_qs | qs.filter(id_jabatan=selected_id)).distinct()
        else:
            self.fields["id_jabatan"].queryset = scoped_qs


class TaJabatanInline(admin.TabularInline):
    model = models.TaJabatan
    form = TaJabatanInlineForm
    formset = TaJabatanInlineFormSet
    fk_name = "nip"
    extra = 0
    autocomplete_fields = ("id_jabatan",)
    readonly_fields = ("created_date", "updated_date", "created_by", "updated_by")
    fields = (
        "id_jabatan",
        "status",
        "jabatan_awal",
        "jabatan_akhir",
        "created_by",
        "created_date",
        "updated_by",
        "updated_date",
    )
    ordering = ("-status", "-jabatan_awal", "-id")

    def get_formset(self, request, obj=None, **kwargs):
        parent_obj = obj
        base_formset = super().get_formset(request, obj, **kwargs)

        class RequestPassingFormSet(base_formset):
            def __init__(self, *args, **formset_kwargs):
                super().__init__(*args, **formset_kwargs)
                self.request = request

            def _construct_form(self, i, **form_kwargs):
                form_kwargs["request"] = request
                form_kwargs["parent_obj"] = parent_obj
                return super()._construct_form(i, **form_kwargs)

        return RequestPassingFormSet
    
    # def get_formset(self, request, obj=None, **kwargs):
    #     parent_obj = obj
    #     base_formset = super().get_formset(request, obj, **kwargs)

    #     class RequestPassingFormSet(base_formset):
    #         def _construct_form(self, i, **form_kwargs):
    #             form_kwargs["request"] = request
    #             form_kwargs["parent_obj"] = parent_obj
    #             return super()._construct_form(i, **form_kwargs)

    #     return RequestPassingFormSet

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)
        request = getattr(form, "request", None)
        if request and not obj.created_by:
            obj.created_by = request.user.username
        if commit:
            obj.save()
        return obj

class MstDataPegawaiAdminForm(forms.ModelForm):
    class Meta:
        model = models.MstDataPegawai
        fields = "__all__"
        widgets = {
            "nip": TextInput(attrs={"size": 40}),
            "nik": TextInput(attrs={"size": 40}),
            "nama_lengkap": TextInput(attrs={"size": 60}),
        }


def reg(model, list_display=None, search_fields=None, list_filter=None):
    class M(admin.ModelAdmin):
        pass
    if list_display:
        M.list_display = list_display
    if search_fields:
        M.search_fields = search_fields
    if list_filter:
        M.list_filter = list_filter
    admin.site.register(model, M)


# ====== JABATAN (MASTER) ======

class MstJabatanAdminForm(forms.ModelForm):
    class Meta:
        model = models.MstJabatan
        fields = "__all__"

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = models.MstJabatan.objects.select_related("instansi")

        # Batasi berdasarkan scope user
        if request and not request.user.is_superuser:
            if request.user.instansi_id:
                scope_ids = get_instansi_scope_ids(request.user.instansi_id)
                qs = qs.filter(instansi_id__in=scope_ids)
            else:
                qs = qs.none()

        # Ambil instansi dari POST atau instance
        instansi_id = None

        if self.data:
            instansi_id = self.data.get("instansi") or self.data.get("instansi_id")

        if not instansi_id and self.instance and self.instance.pk:
            instansi_id = self.instance.instansi_id

        if instansi_id:
            qs = qs.filter(instansi_id=instansi_id)

        # Jangan boleh parent = diri sendiri
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        self.fields["parent"].queryset = qs


@admin.register(models.MstJabatan)
class MstJabatanAdmin(DraggableMPTTAdmin):
    form = MstJabatanAdminForm
    mptt_indent_field = "nama_jabatan"
    expand_tree_by_default = True
    ordering = ("tree_id", "lft")
    sortable_by = ()

    list_display = (
        "tree_actions",
        "indented_title",
        "instansi",
        "level_jabatan",
        "jenis_jabatan",
        "no_urut",
    )

    search_fields = ("nama_jabatan", "instansi__nama")
    list_filter = ("level_jabatan", "jenis_jabatan", "instansi")
    list_select_related = ("instansi", "parent")
    autocomplete_fields = ("instansi", "parent")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.is_staff and request.user.instansi_id:
            scope_ids = get_instansi_scope_ids(request.user.instansi_id)
            return qs.filter(instansi_id__in=scope_ids)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class RequestAwareForm(Form):
            def __init__(self2, *args, **kw):
                kw["request"] = request
                super().__init__(*args, **kw)

        return RequestAwareForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instansi" and not request.user.is_superuser:
            if request.user.instansi_id:
                scope_ids = get_instansi_scope_ids(request.user.instansi_id)
                kwargs["queryset"] = models.RefInstansi.objects.filter(id__in=scope_ids)
            else:
                kwargs["queryset"] = models.RefInstansi.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_filter(self, request):
        lf = list(super().get_list_filter(request))
        if not request.user.is_superuser:
            lf = [x for x in lf if x != "instansi"]
        return lf


# ====== SURAT + INLINE TAHAPAN ======

class SuratTahapanInline(admin.TabularInline):
    model = models.SuratTahapan
    extra = 0
    ordering = ("seq_tahapan",)
    show_change_link = True

    # Pakai FK (tanpa instansi_ref dulu).
    fields = (
        "seq_tahapan",
        "pejabat",
        "sign_type_ref",
        "sign_status_ref",
        "sign_date",
    )
    readonly_fields = ("sign_date",)

    autocomplete_fields = ("pejabat", "sign_type_ref", "sign_status_ref")


@admin.register(models.Surat)
class SuratAdmin(admin.ModelAdmin):
    list_display = ("id_surat","nomor_surat","judul_surat","instansi_ref","is_finish","create_date", "file_surat_link", "file_unsigned_link", "file_signed_link")
    list_filter = ("is_finish","instansi_ref")
    inlines = [SuratTahapanInline]
    autocomplete_fields = ("created_by","instansi_ref",)
    search_fields = (
        "id_surat",
        "nomor_surat",
        "judul_surat",
        "tujuan_surat",
        "id_dokumen",
        # FK: arahkan ke field string/hash di target model
        "created_by__nip_hash",
        "created_by__nama_lengkap_hash",
        # kalau instansi punya kolom nama (sesuaikan)
        "instansi_ref__nama",
    )
    def file_surat_link(self, obj):
        if not obj.file_surat:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">📄 Buka PDF</a>',
            obj.file_surat.url
        )
    file_surat_link.short_description = "Dokumen Surat"
    
    def file_unsigned_link(self, obj):
        if not obj.file_unsigned:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">📄 Buka PDF</a>',
            obj.file_unsigned.url
        )

    file_unsigned_link.short_description = "Dokumen Unsigned"


    def file_signed_link(self, obj):
        if not obj.file_signed:
            return "-"
        return format_html(
            '<a href="{}" target="_blank">📄 Buka PDF</a>',
            obj.file_signed.url
        )

    file_signed_link.short_description = "Dokumen Signed"

    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)

        term = (search_term or "").strip()
        if term.isdigit():
            # exact id_surat match (BigInteger)
            qs = qs | queryset.filter(id_surat=int(term))

        return qs, use_distinct


# Optional: list view terpisah SuratTahapan (kalau mau tetap ada).
@admin.register(models.SuratTahapan)
class SuratTahapanAdmin(admin.ModelAdmin):
    list_display = ("id_tahapan","surat","seq_tahapan","pejabat","sign_type_ref","sign_status_ref","sign_date")

    # Sesuaikan dengan field MstDataPegawai yang kamu punya.
    search_fields = (
        "pejabat__nip",
        "pejabat__nama_lengkap",
        "pejabat__id_jabatan__nama_jabatan",
        "instansi",
        "instansi_kode",
    )

    # instansi_ref dihapus karena fieldnya belum ada (kita tunda).
    list_filter = ("sign_type_ref","sign_status_ref")

    autocomplete_fields = ("surat","pejabat","sign_type_ref","sign_status_ref")


@admin.register(models.RefInstansi)
class RefInstansiAdmin(admin.ModelAdmin):

    list_display = (
        "nama",
        "aktif",
        "hari_kerja",
        "login_terakhir",
    )

    list_display_links = ("nama",)

    search_fields = (
        "nama",
    )

    ordering = ("nama",)
    list_per_page = 50


@admin.register(models.MstDataPegawai)
class MstDataPegawaiAdmin(admin.ModelAdmin):
    form = MstDataPegawaiAdminForm
    inlines = [TaJabatanInline]
    list_display = (
        "nip_masked",
        "nik_masked",
        "nama_masked",
        "id_instansi",
        "id_jabatan",
        "is_active",
        "specimen_status",
        "specimen_updated_at",
    )
    ordering = ("id",)
    list_filter = ("is_active", "id_instansi")
    list_select_related = ("id_instansi", "id_jabatan")

    # IMPORTANT: untuk autocomplete di model lain yang mengarah ke pegawai
    search_fields = ("nip_hash", "nik_hash", "nama_lengkap_hash")

    # FK nyaman
    autocomplete_fields = ("id_instansi", "id_jabatan")

    readonly_fields = (
        "nip_hash",
        "nik_hash",
        "nama_lengkap_hash",
        "specimen_updated_at",
        "specimen_paraf_preview",
        "specimen_ttd_preview",
    )

    fieldsets = (
        (None, {
            "fields": (
                "nip",
                "nik",
                "nama_lengkap",
                "id_instansi",
                "id_jabatan",
                "is_active",
            )
        }),
        ("Spesimen", {
            "fields": (
                "specimen_paraf",
                "specimen_paraf_preview",
                "specimen_ttd",
                "specimen_ttd_preview",
                "specimen_updated_at",
            )
        }),
        ("Profil", {
            "fields": (
                "tempat_lahir",
                "tgl_lahir",
                "golongan",
                "eselon",
                "pendidikan",
                "keterangan",
            )
        }),
        ("Index (readonly)", {
            "classes": ("collapse",),
            "fields": ("nip_hash", "nik_hash", "nama_lengkap_hash"),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        self._request = request
        return super().changelist_view(request, extra_context)

    @admin.display(description="NIP")
    def nip_masked(self, obj):
        request = getattr(self, "_request", None)
        if request and request.user.is_superuser:
            return obj.nip
        return mask_mid(obj.nip, 3, 3)


    @admin.display(description="NIK")
    def nik_masked(self, obj):
        request = getattr(self, "_request", None)
        if request and request.user.is_superuser:
            return obj.nik
        return mask_mid(obj.nik, 3, 3)


    @admin.display(description="Nama")
    def nama_masked(self, obj):
        request = getattr(self, "_request", None)
        n = (obj.nama_lengkap or "").strip()

        if request and request.user.is_superuser:
            return n

        if not n:
            return "-"
        return (n[:2] + "***") if len(n) > 2 else (n[0] + "***")

    # ===== spesimen helpers =====
    @admin.display(description="Spesimen")
    def specimen_status(self, obj):
        p = bool(getattr(obj, "specimen_paraf", None))
        t = bool(getattr(obj, "specimen_ttd", None))
        if p and t:
            return "Paraf+TTD"
        if p:
            return "Paraf"
        if t:
            return "TTD"
        return "-"

    @admin.display(description="Preview Paraf")
    def specimen_paraf_preview(self, obj):
        f = getattr(obj, "specimen_paraf", None)
        if not f:
            return "-"
        try:
            return format_html('<a href="{}" target="_blank">Buka Paraf</a>', f.url)
        except Exception:
            return "-"

    @admin.display(description="Preview TTD")
    def specimen_ttd_preview(self, obj):
        f = getattr(obj, "specimen_ttd", None)
        if not f:
            return "-"
        try:
            return format_html('<a href="{}" target="_blank">Buka TTD</a>', f.url)
        except Exception:
            return "-"

    def save_model(self, request, obj, form, change):
        # timestamp spesimen berubah
        if change and ("specimen_paraf" in form.changed_data or "specimen_ttd" in form.changed_data):
            obj.specimen_updated_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_search_results(self, request, queryset, search_term):
        """
        Search/autocomplete:
        - user ketik NIP/NIK/Nama plaintext
        - kita ubah ke hash -> exact match
        """
        qs, use_distinct = super().get_search_results(request, queryset, search_term)

        term = (search_term or "").strip()
        if not term:
            return qs, use_distinct

        h = hash_lookup(term)
        q2 = queryset.filter(nip_hash=h) | queryset.filter(nik_hash=h) | queryset.filter(nama_lengkap_hash=h)

        try:
            qs = qs.union(q2)
        except Exception:
            qs = (qs | q2)

        return qs, use_distinct
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.is_staff and request.user.instansi_id:
            scope_ids = get_instansi_scope_ids(request.user.instansi_id)
            return qs.filter(id_instansi_id__in=scope_ids)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Batasi pilihan instansi saat edit/create pegawai
        if db_field.name == "id_instansi" and not request.user.is_superuser:
            if request.user.instansi_id:
                scope_ids = get_instansi_scope_ids(request.user.instansi_id)
                kwargs["queryset"] = models.RefInstansi.objects.filter(id__in=scope_ids)
            else:
                kwargs["queryset"] = models.RefInstansi.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # timestamp spesimen berubah
        if change and ("specimen_paraf" in form.changed_data or "specimen_ttd" in form.changed_data):
            obj.specimen_updated_at = timezone.now()

        # Jika admin instansi dan mencoba isi di luar scope, paksa ke instansi admin
        if (not request.user.is_superuser) and request.user.instansi_id:
            scope_ids = set(get_instansi_scope_ids(request.user.instansi_id))
            if obj.id_instansi_id not in scope_ids:
                obj.id_instansi_id = request.user.instansi_id

        super().save_model(request, obj, form, change)
    
    def get_list_filter(self, request):
        lf = list(super().get_list_filter(request))
        if not request.user.is_superuser:
            lf = [x for x in lf if x != "id_instansi"]
        return lf


reg(models.TteInstansi, list_display=("id","tins_nama","create_date"), search_fields=("tins_nama",))
reg(models.TteJabatan, list_display=("id","tjab_nama","tjab_instansi","tjab_parent_jabatan"), search_fields=("tjab_nama",), list_filter=("tjab_instansi",))
reg(models.TteUser, list_display=("id_usr","nama_usr","full_usr","email_usr","is_active","instansi_fk","jabatan_loc"), search_fields=("nama_usr","full_usr","email_usr","tlp_usr"), list_filter=("is_active","instansi_fk"))


@admin.register(models.Asda)
class AsdaAdmin(admin.ModelAdmin):
    list_display = ("id_loc_asda", "nama_jabatan", "pegawai", "jenis_jabatan", "id_instansi")
    search_fields = ("id_loc_asda", "nama_jabatan", "pegawai__nip", "pegawai__nama", "pegawai__nama_lengkap")
    list_filter = ("jenis_jabatan", "id_instansi")
    autocomplete_fields = ("pegawai",)   # ✅ ini yang bikin field pegawai jadi autocomplete

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("pegawai")

@admin.register(models.AsdaSkpd)
class AsdaSkpdAdmin(admin.ModelAdmin):
    list_display = ("id_asda_skpd", "asda", "skpd", "kepala_pegawai")
    search_fields = (
        "asda__id_loc_asda",
        "asda__nama_jabatan",
        "skpd__id",        # sesuaikan
        "skpd__nama",      # sesuaikan
        "kepala_pegawai__nip",
        "kepala_pegawai__nama",
        "kepala_pegawai__nama_lengkap",
    )
    list_filter = ("asda", "skpd")
    autocomplete_fields = ("asda", "skpd", "kepala_pegawai")  # ✅ ini yang kamu mau

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("asda", "skpd", "kepala_pegawai")


reg(models.RoleUsr, list_display=("id_role","role_name","id_group"), search_fields=("role_name",), list_filter=("id_group",))
reg(models.Menu, list_display=("id_menu","nama_menu","url_menu","parent_menu","active_menu","seq_menu"), search_fields=("nama_menu","url_menu"), list_filter=("active_menu","parent_menu"))
reg(models.MenuFeature, list_display=("id_feture","id_role","id_menu","feature"), list_filter=("id_role","id_menu","feature"))

reg(models.Preferences, list_display=("preference_id","preference_name","preference_created"), search_fields=("preference_name",))
reg(models.PreferencesDetail, list_display=("preference_id","preference_name","preference_parent","preference_created"), search_fields=("preference_name",), list_filter=("preference_parent",))
reg(models.RefTemplate, list_display=("id_tmp","nama_template","file_template"), search_fields=("nama_template","file_template"))


@admin.register(models.Notifikasi)
class NotifikasiAdmin(admin.ModelAdmin):
    list_display = ("id", "display_pegawai", "type", "no_surat", "created")
    search_fields = (
        "pegawai__nip",
        "pegawai__nama",
        "pegawai__nama_lengkap",
        "no_surat",
        "perihal",
        "message",
    )
    list_filter = ("type", "created")
    date_hierarchy = "created"
    ordering = ("-created", "-id")

    autocomplete_fields = ("pegawai",)

    @admin.display(description="Pegawai", ordering="pegawai__nip")
    def display_pegawai(self, obj):
        if not obj.pegawai_id or not obj.pegawai:
            return "-"
        nip = getattr(obj.pegawai, "nip", "")
        nama = getattr(obj.pegawai, "nama_lengkap", None) or getattr(obj.pegawai, "nama", "")
        return f"{nip} - {nama}" if (nip or nama) else str(obj.pegawai)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("pegawai")



@admin.register(models.TelegramNotif)
class TelegramNotifAdmin(admin.ModelAdmin):
    list_display = ("tn_id", "display_pegawai", "tn_chat_id", "tn_status")
    search_fields = (
        "pegawai__nip",
        "pegawai__nama",
        "tn_chat_id",
    )
    list_filter = ("tn_status",)
    autocomplete_fields = ("pegawai",)

    @admin.display(description="Pegawai", ordering="pegawai__nip")
    def display_pegawai(self, obj):
        if not obj.pegawai:
            return "-"
        return f"{obj.pegawai.nip} - {obj.pegawai.nama_lengkap}"


@admin.register(models.LogApp)
class LogAppAdmin(admin.ModelAdmin):
    list_display = ("la_id", "la_type", "display_user", "display_pegawai", "la_time")
    list_filter = ("la_type", "la_time", "user", "pegawai")
    date_hierarchy = "la_time"
    ordering = ("-la_time", "-la_id")

    # INI KUNCI: bikin FK jadi select2 + ajax
    autocomplete_fields = ("user", "pegawai")

    search_fields = (
        "la_type",
        "la_desc",
        "user__username",
        "user__full_name",
        "pegawai__nip",
        "pegawai__nama",
        "pegawai__nama_lengkap",
    )

    @admin.display(description="User", ordering="user__username")
    def display_user(self, obj):
        return getattr(obj.user, "username", None) or getattr(obj.user, "full_name", None) or "-"

    @admin.display(description="Pegawai", ordering="pegawai__nip")
    def display_pegawai(self, obj):
        if not obj.pegawai_id:
            return "-"
        nip = getattr(obj.pegawai, "nip", None)
        nama = getattr(obj.pegawai, "nama", None) or getattr(obj.pegawai, "nama_lengkap", None)
        return f"{nip} - {nama}" if nip and nama else (nip or nama or "-")

    def get_queryset(self, request):
        # optional: kecilkan beban list view
        qs = super().get_queryset(request)
        return qs.select_related("user", "pegawai")


@admin.register(models.LogUsr)
class LogUsrAdmin(admin.ModelAdmin):
    list_display = ("id_log", "display_user", "display_pegawai", "waktu", "kategori", "display_ipaddr")
    list_filter = ("kategori", "waktu", "user", "pegawai")
    date_hierarchy = "waktu"
    ordering = ("-waktu", "-id_log")

    autocomplete_fields = ("user", "pegawai")

    search_fields = (
        "user__username",
        "user__full_name",
        "pegawai__nip",
        "pegawai__nama",
        "pegawai__nama_lengkap",
        "ipaddr",
    )

    @admin.display(description="User", ordering="user__username")
    def display_user(self, obj):
        return getattr(obj.user, "username", None) or getattr(obj.user, "full_name", None) or "-"

    @admin.display(description="Pegawai", ordering="pegawai__nip")
    def display_pegawai(self, obj):
        if not obj.pegawai_id:
            return "-"
        nip = getattr(obj.pegawai, "nip", None)
        nama = getattr(obj.pegawai, "nama", None) or getattr(obj.pegawai, "nama_lengkap", None)
        return f"{nip} - {nama}" if nip and nama else (nip or nama or "-")

    @admin.display(description="IP Address")
    def display_ipaddr(self, obj):
        try:
            return obj.ipaddr or "-"
        except Exception:
            return "-"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "pegawai")


@admin.register(models.LogBsre)
class LogBsreAdmin(admin.ModelAdmin):
    list_display = ("display_pegawai", "display_surat", "waktu", "kategori", "file", "msg_log")
    list_filter = ("kategori", "waktu")
    date_hierarchy = "waktu"
    ordering = ("-waktu", "-id_log")

    list_display_links = ("display_pegawai",)

    search_fields = (
        "pegawai__nip",
        "pegawai__nama",
        "pegawai__nama_lengkap",
        "file",
        "msg_log",
        "surat__nomor",
        "surat__perihal"
    )

    @admin.display(description="Pegawai", ordering="pegawai__nip")
    def display_pegawai(self, obj):
        if not obj.pegawai_id:
            return "-"
        nip = getattr(obj.pegawai, "nip", None)
        nama = getattr(obj.pegawai, "nama", None) or getattr(obj.pegawai, "nama_lengkap", None)
        return f"{nip} - {nama}" if nip and nama else (nip or nama or "-")

    @admin.display(description="Surat")
    def display_surat(self, obj):
        if not obj.surat_id or not obj.surat:
            return "-"
        nomor = getattr(obj.surat, "nomor", None)
        perihal = getattr(obj.surat, "perihal", None)
        return f"{nomor} - {perihal}" if nomor and perihal else (nomor or perihal or f"Surat #{obj.surat_id}")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("pegawai", "surat")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Setting)
class SettingAdmin(admin.ModelAdmin):

    list_display = (
        "nama_web",
        "telepon_web",
        "email_web",
        "is_maintenance",
    )

    search_fields = (
        "nama_web",
        "email_web",
    )

    list_filter = (
        "is_maintenance",
    )

    list_display_links = (
        "nama_web",
    )

    ordering = ("id_set",)


reg(models.SuratFinish, list_display=("id","finish"), search_fields=("finish",))
reg(models.SuratMsg, list_display=("id_msg","id_surat","msg_create","msg_date"), search_fields=("id_surat","msg_create"))
reg(models.SuratSignStatus, list_display=("id_status","nama_status"), search_fields=("nama_status",))
reg(models.SuratSignType, list_display=("id_sign","nama_sign"), search_fields=("nama_sign",))
reg(models.TmpSrtDet, list_display=("id_tmp","id_req","id_ref_template","id_tr","row_seq"), search_fields=("id_req",), list_filter=("id_ref_template",))
reg(models.TmpSrtFile, list_display=("id_srt_file","id_tr","file_name"), search_fields=("file_name",))

class SuratTemplateSpecimenSlotInline(admin.TabularInline):
    model = models.SuratTemplateSpecimenSlot
    extra = 1
    min_num = 0
    ordering = ("urutan_signer",)

    fields = (
        "urutan_signer",
        "nama_slot",
        "placement_type",
        "marker_text",
        "pointer_text",
        "pointer_mode",
        "offset_x",
        "offset_y",
        "width",
        "height",
        "fallback_page",
        "fallback_x",
        "fallback_y",
        "is_active",
    )

@admin.register(models.SuratTemplate)
class SuratTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "nama",
        "kode",
        "is_active",
        "stamp_mode",
        "specimen_mode",
        "qr_marker_text",
        "ttd_marker_text",
    )

    list_display_links = ("nama",)

    search_fields = (
        "kode",
        "nama",
        "deskripsi",
        "qr_marker_text",
        "ttd_marker_text",
    )

    list_filter = (
        "is_active",
        "stamp_mode",
        "specimen_mode",
    )

    ordering = ("nama",)

    list_per_page = 50

    readonly_fields = ("id_template",)

    fieldsets = (
        ("Identitas Template", {
            "fields": (
                "id_template",
                "kode",
                "nama",
                "deskripsi",
                "is_active",
            )
        }),

        ("Marker QR / TTD", {
            "fields": (
                "qr_marker_text",
                "ttd_marker_text",
                "stamp_mode",
            ),
            "description": (
                "Marker boleh kosong → fallback ke Setting. "
                "ttd_marker_text bisa '[TTD]' atau '[TTD{n}]'."
            ),
        }),

        ("Override Ukuran QR / TTD", {
            "fields": (
                ("qr_width", "qr_height"),
                ("qr_x", "qr_y"),
                ("ttd_width", "ttd_height"),
            ),
            "description": "Jika kosong → memakai Setting global."
        }),

        ("Specimen (Generated / Upload)", {
            "fields": (
                "specimen_mode",
                ("specimen_width", "specimen_height"),
                ("specimen_bg_color", "specimen_border_color"),
            ),
            "description": (
                "upload = pakai file specimen pegawai.\n"
                "generated = sistem membuat spesimen otomatis."
            ),
        }),
    )

    inlines = [
        SuratTemplateSpecimenSlotInline
    ]

    actions = ("set_active", "set_inactive")

    @admin.action(description="Set aktif")
    def set_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} template berhasil diaktifkan.")

    @admin.action(description="Set nonaktif")
    def set_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} template berhasil dinonaktifkan.")
from django.db import models
from core.upload_paths import surat_pdf_upload_to
from core.validators import pdf_extension_validator, validate_pdf_magic, validate_max_10mb
from core.fields import EncryptedTextField
from core.crypto import hash_lookup
from django.conf import settings
from django.core.validators import FileExtensionValidator
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError
import os


def upload_to_tahapan_signed(instance, filename):
    base, ext = os.path.splitext(filename or "")
    ext = (ext or ".pdf").lower()
    v = instance.signed_version_no or 0
    return f"signed/tahapan/{instance.id_tahapan}/ttd_{instance.id_tahapan}_v{v}{ext}"

def specimen_upload_to(instance, filename):
    return f"specimen/pegawai/{instance.id}/{filename}"

def setting_upload_to(instance, filename):
    return f"setting/assets/{filename}"

class Asda(models.Model):
    id_loc_asda = models.AutoField(primary_key=True)

    id_jabatan = models.IntegerField(null=True, blank=True)
    id_instansi = models.IntegerField(null=True, blank=True)
    id_parent = models.IntegerField(null=True, blank=True)

    nama_jabatan = models.CharField(max_length=512, null=True, blank=True)

    # legacy (nanti di-drop)
    nama_pejabat = models.CharField(max_length=512, null=True, blank=True)

    jenis_jabatan = models.CharField(max_length=16)  # NOT NULL di DB

    # FK PDP
    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="asda_set",
        db_column="pegawai_id",
    )

    def __str__(self):
        return self.nama_jabatan

    class Meta:
        db_table = "asda"
        managed = False
        verbose_name = "ASDA"
        verbose_name_plural = "ASDA"


class AsdaSkpd(models.Model):
    id_asda_skpd = models.AutoField(primary_key=True)

    asda = models.ForeignKey(
        "core.Asda",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="skpd_set",
        db_column="id_asda",
        to_field="id_loc_asda",
    )

    skpd = models.ForeignKey(
        "core.RefInstansi",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="asda_skpd_set",
        db_column="id_skpd",
        to_field="id",
    )

    kepala_pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="asda_skpd_kepala_set",
        db_column="kepala_pegawai_id",
    )

    class Meta:
        db_table = "asda_skpd"
        managed = False
        verbose_name = "ASDA-SKPD"
        verbose_name_plural = "ASDA-SKPD"



class LogApp(models.Model):
    la_id = models.BigAutoField(primary_key=True)
    la_type = models.CharField(max_length=255, null=True, blank=True)

    # PDP: jangan simpan la_usr plaintext kalau itu NIP/nama/username.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_app_set",
        db_column="user_id",
    )

    # Optional: kalau butuh referensi langsung ke pegawai
    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_app_set",
        db_column="pegawai_id",
    )

    la_desc = models.TextField(null=True, blank=True)
    la_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "log_app"
        verbose_name = "Log App"
        verbose_name_plural = "Log App"


class LogBsre(models.Model):
    id_log = models.AutoField(primary_key=True)

    # PDP: ganti id_usr/nm_usr/jbt_usr/ins_usr/nik => FK pegawai
    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_bsre_set",
        db_column="pegawai_id",
    )

    # Kalau mau relasi ke surat, idealnya BIGINT FK ke surat.id_surat
    surat = models.ForeignKey(
        "core.Surat",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_bsre_set",
        db_column="surat_id",
    )

    file = models.CharField(max_length=256, null=True, blank=True)
    msg_log = models.TextField(null=True, blank=True)
    waktu = models.DateTimeField(null=True, blank=True)
    kategori = models.IntegerField(null=True, blank=True, help_text="2 = fail")

    ipaddr = EncryptedTextField(null=True, blank=True)

    class Meta:
        db_table = "log_bsre"
        verbose_name = "Log BSrE"
        verbose_name_plural = "Log BSrE"


class LogUsr(models.Model):
    id_log = models.AutoField(primary_key=True)

    # PDP: ganti id_usr + inputpass => user FK (atau pegawai FK)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_usr_set",
        db_column="user_id",
    )

    # optional, kalau perlu akses cepat pegawai
    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="log_usr_set",
        db_column="pegawai_id",
    )

    waktu = models.DateTimeField(null=True, blank=True)
    kategori = models.IntegerField(null=True, blank=True)

    # PDP: pertimbangkan hash / masked
    ipaddr = EncryptedTextField(null=True, blank=True)
    aktivitas = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = "log_usr"
        verbose_name = "Log User"
        verbose_name_plural = "Log User"


class Menu(models.Model):
    id_menu = models.AutoField(primary_key=True)
    nama_menu = models.CharField(max_length=128, null=True, blank=True)
    url_menu = models.CharField(max_length=256, null=True, blank=True)
    icon_menu = models.CharField(max_length=128, null=True, blank=True)
    grandparent_menu = models.SmallIntegerField()
    parent_menu = models.SmallIntegerField()
    active_menu = models.SmallIntegerField()
    seq_menu = models.SmallIntegerField(null=True, blank=True)
    additional = models.CharField(max_length=64, null=True, blank=True)
    typeM = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        db_table = "menu"
        verbose_name = "Menu"
        verbose_name_plural = "Menu"


class MenuFeature(models.Model):
    id_feture = models.AutoField(primary_key=True)
    id_role = models.SmallIntegerField(null=True, blank=True)
    id_menu = models.SmallIntegerField(null=True, blank=True)
    feature = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "menu_feature"
        verbose_name = "Menu Feature"
        verbose_name_plural = "Menu Feature"


class RefInstansi(models.Model):
    id = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    alamat = models.TextField(null=True, blank=True)
    kota = models.CharField(max_length=255, null=True, blank=True)
    id_kabkota = models.IntegerField(null=True, blank=True)
    id_provinsi = models.IntegerField(null=True, blank=True)
    telepon = models.CharField(max_length=255, null=True, blank=True)
    kode_pos = models.CharField(max_length=10, null=True, blank=True)
    aktif = models.BooleanField(default=False)
    nama_pj = models.CharField(max_length=255, null=True, blank=True)
    nip_pj = models.CharField(max_length=255, null=True, blank=True)
    telepon_pj = models.CharField(max_length=255, null=True, blank=True)
    email_pj = models.CharField(max_length=255, null=True, blank=True)
    hari_kerja = models.SmallIntegerField(default=5)
    login_terakhir = models.DateField(null=True, blank=True)
    status_aktif = models.IntegerField(default=1, null=True, blank=True)
    tanggal_update_peta = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        db_column="parent_id",
    )

    TIPE_CHOICES = (
        ("SKPD", "SKPD"),
        ("UNIT", "UNIT"),
    )
    tipe = models.CharField(max_length=10, choices=TIPE_CHOICES, default="SKPD")

    def clean(self):
        if self.tipe == "SKPD" and self.parent_id is not None:
            raise ValidationError({"parent": "SKPD tidak boleh punya parent."})
        if self.tipe == "UNIT" and self.parent_id is None:
            raise ValidationError({"parent": "UNIT harus punya parent (SKPD)."})
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({"parent": "Parent tidak boleh dirinya sendiri."})

    class Meta:
        db_table = "ref_instansi"
        verbose_name = "Instansi"
        verbose_name_plural = "Instansi"

    def __str__(self):
        if self.parent_id:
            return f"{self.nama} (Unit - {self.parent.nama})"
        return f"{self.nama} (SKPD)"


class MstJabatan(MPTTModel):
    """
    - id_jabatan: PK
    - id_instansi: FK ke ref_instansi.id
    - id_parent: FK ke mst_jabatan.id_jabatan (self-referential)
    """

    id_jabatan = models.AutoField(primary_key=True)

    instansi = models.ForeignKey(
        "RefInstansi",
        db_column="id_instansi",
        on_delete=models.CASCADE,     # umumnya jabatan ikut instansi
        related_name="jabatan_set",
        verbose_name="Instansi",
    )

    parent = TreeForeignKey(
        "self",
        to_field="id_jabatan",
        db_column="id_parent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="Parent Jabatan",
    )

    JENIS_JABATAN_CHOICES = (
        ("S", "Struktural"),
        ("F", "Fungsional"),
    )

    no_urut = models.IntegerField(null=True, blank=True)
    level_jabatan = models.IntegerField(default=4)
    nama_jabatan = models.CharField(max_length=100, null=True, blank=True)
    ikhtisar_jabatan = models.TextField(null=True, blank=True)
    jenis_jabatan = models.CharField(max_length=1, null=True, blank=True, choices=JENIS_JABATAN_CHOICES)

    class Meta:
        db_table = "mst_jabatan"
        verbose_name = "Jabatan (Master)"
        verbose_name_plural = "Jabatan (Master)"
        indexes = [
            models.Index(fields=["instansi"], name="mstjab_instansi_idx"),
            models.Index(fields=["parent"], name="mstjab_parent_idx"),
        ]

    def clean(self):
        super().clean()

        # parent boleh null
        if not self.parent_id:
            return

        # Kalau level != 1, parent WAJIB satu instansi
        if (self.level_jabatan or 0) != 1:
            if self.parent and self.parent.instansi_id != self.instansi_id:
                raise ValidationError({
                    "parent": "Parent lintas instansi hanya diizinkan untuk level jabatan = 1."
                })

    def __str__(self):
        return f"{self.nama_jabatan or '-'} ({self.instansi.nama})"


class Notifikasi(models.Model):
    id = models.BigAutoField(primary_key=True)
    token = models.CharField(max_length=256, null=True, blank=True)

    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="notifikasi_set",
        db_column="pegawai_id",
    )

    message = models.CharField(max_length=100, null=True, blank=True)
    url = models.CharField(max_length=100, null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True, db_index=True)

    class Type(models.TextChoices):
        PARAF = "1", "Paraf"
        TTD = "2", "TTD"
        PEMBUAT = "3", "Pembuat Surat"
        SELESAI = "4", "Surat Selesai"

    type = models.CharField(
        max_length=20, null=True, blank=True,
        choices=Type.choices,
        db_index=True
    )

    perihal = models.CharField(max_length=512, null=True, blank=True)
    no_surat = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = "notifikasi"
        verbose_name = "Notifikasi"
        verbose_name_plural = "Notifikasi"


class Preferences(models.Model):
    preference_id = models.AutoField(primary_key=True)
    preference_name = models.CharField(max_length=256, null=True, blank=True)
    preference_value = models.TextField(null=True, blank=True)
    preference_desc = models.TextField(null=True, blank=True)
    preference_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "preferences"
        verbose_name = "Preferences"
        verbose_name_plural = "Preferences"


class PreferencesDetail(models.Model):
    preference_id = models.AutoField(primary_key=True)
    preference_name = models.CharField(max_length=256, null=True, blank=True)
    preference_value = models.TextField(null=True, blank=True)
    preference_desc = models.TextField(null=True, blank=True)
    preference_parent = models.IntegerField(null=True, blank=True)
    preference_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "preferences_detail"
        verbose_name = "Preferences Detail"
        verbose_name_plural = "Preferences Detail"


class RefTemplate(models.Model):
    id_tmp = models.AutoField(primary_key=True)
    nama_template = models.CharField(max_length=255, null=True, blank=True)
    nip_create = models.BinaryField(max_length=16, null=True, blank=True)
    file_template = models.CharField(max_length=255, null=True, blank=True)
    f1 = models.CharField(max_length=255, null=True, blank=True)
    f2 = models.CharField(max_length=255, null=True, blank=True)
    f3 = models.CharField(max_length=255, null=True, blank=True)
    f4 = models.CharField(max_length=255, null=True, blank=True)
    f5 = models.CharField(max_length=255, null=True, blank=True)
    f6 = models.CharField(max_length=255, null=True, blank=True)
    f7 = models.CharField(max_length=255, null=True, blank=True)
    f8 = models.CharField(max_length=255, null=True, blank=True)
    f9 = models.CharField(max_length=255, null=True, blank=True)
    f10 = models.CharField(max_length=255, null=True, blank=True)
    f11 = models.CharField(max_length=255, null=True, blank=True)
    f12 = models.CharField(max_length=255, null=True, blank=True)
    f13 = models.CharField(max_length=255, null=True, blank=True)
    f14 = models.CharField(max_length=255, null=True, blank=True)
    f15 = models.CharField(max_length=255, null=True, blank=True)
    f16 = models.CharField(max_length=255, null=True, blank=True)
    f17 = models.CharField(max_length=255, null=True, blank=True)
    f18 = models.CharField(max_length=255, null=True, blank=True)
    f19 = models.CharField(max_length=255, null=True, blank=True)
    f20 = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "ref_template"
        verbose_name = "Template"
        verbose_name_plural = "Template"


class RoleUsr(models.Model):
    id_role = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=64, null=True, blank=True)
    id_group = models.IntegerField(null=True, blank=True, help_text="1 user, 2 admin")

    class Meta:
        db_table = "role_usr"
        verbose_name = "Role"
        verbose_name_plural = "Role"

    def __str__(self):
        return self.role_name or f"Role #{self.id_role}"


class Setting(models.Model):
    id_set = models.AutoField(primary_key=True)
    nama_web = models.CharField(max_length=128, null=True, blank=True)
    deskripsi = models.TextField(null=True, blank=True)
    telepon_web = models.CharField(max_length=16, null=True, blank=True)
    location = models.CharField(max_length=1024, null=True, blank=True)
    email_web = models.CharField(max_length=128, null=True, blank=True)
    alamat_web = models.TextField(null=True, blank=True)
    logo_web = models.CharField(max_length=254, null=True, blank=True)
    popup = models.CharField(max_length=254, null=True, blank=True)
    p_sta = models.IntegerField(default=2)
    meta_keyword = models.TextField(null=True, blank=True)
    is_maintenance = models.CharField(max_length=4, default="N", null=True, blank=True)
    qr_logo = models.FileField(
        upload_to=setting_upload_to,
        null=True, blank=True,
        validators=[FileExtensionValidator(["png"])],
        help_text="Logo PNG untuk ditaruh di tengah QR (disimpan di MinIO)."
    )

    qr_marker_text = models.CharField(
        max_length=32, null=True, blank=True, default="[QR]",
        help_text="Marker teks untuk posisi QR di template PDF."
    )

    ttd_marker_text = models.CharField(
        max_length=32, null=True, blank=True, default="[TTD]",
        help_text="Marker teks untuk posisi spesimen/paraf di template PDF."
    )

    qr_width = models.IntegerField(default=110)
    qr_height = models.IntegerField(default=110)

    # ukuran spesimen (points)
    ttd_width = models.IntegerField(default=120)
    ttd_height = models.IntegerField(default=60)

    # mode stamping:
    # - "marker": pakai marker jika ada, fallback jika tidak
    # - "all_markers": stamp di semua marker yang ketemu (multi page)
    stamp_mode = models.CharField(
        max_length=16,
        default="marker",
        choices=[("marker","Marker"), ("all_markers","All Markers")],
    )

    # fallback halaman untuk QR/TTD jika marker tidak ditemukan:
    # 1 = halaman 1, 0 = last page
    qr_fallback_page = models.IntegerField(default=0)   # 0 = last
    ttd_fallback_page = models.IntegerField(default=0)

    # fallback koordinat (points) jika marker tidak ditemukan
    qr_fallback_x = models.IntegerField(default=450)
    qr_fallback_y = models.IntegerField(default=80)

    ttd_fallback_x = models.IntegerField(default=320)
    ttd_fallback_y = models.IntegerField(default=80)

    bsre_logo = models.FileField(
        upload_to=setting_upload_to,
        null=True, blank=True,
        validators=[FileExtensionValidator(["png"])],
        help_text="Logo PNG BSrE untuk footnote (disimpan di MinIO)."
    )

    footnote_enabled = models.BooleanField(default=True)

    footnote_marker_text = models.CharField(
        max_length=32, null=True, blank=True, default="[FOOTNOTE]",
        help_text="Marker teks untuk posisi footnote di template PDF."
    )

    footnote_text = models.TextField(
        null=True, blank=True,
        default=(
            "Dokumen ini telah ditandatangani secara elektronik menggunakan sertifikat elektronik yang\n"
            "diterbitkan oleh Balai Besar Sertifikasi Elektronik (BSrE) Badan Siber dan Sandi Negara"
        )
    )

    # fallback posisi footnote (points)
    footnote_fallback_page = models.IntegerField(default=0)  # 0 = last
    footnote_fallback_x = models.IntegerField(default=60)
    footnote_fallback_y = models.IntegerField(default=35)

    # layout (points)
    footnote_box_width = models.IntegerField(default=480)
    footnote_font_size = models.IntegerField(default=8)
    footnote_line_gap = models.IntegerField(default=10)

    # logo ukuran (points)
    footnote_logo_w = models.IntegerField(default=45)
    footnote_logo_h = models.IntegerField(default=45)

    verify_base_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Base URL untuk verifikasi QR TTE (contoh: https://tte.bekasikab.go.id/verifikasi)"
    )

    class Meta:
        db_table = "setting"
        verbose_name = "Setting"
        verbose_name_plural = "Setting"


class SuratTemplate(models.Model):
    id_template = models.AutoField(primary_key=True)
    kode = models.CharField(max_length=50, unique=True)
    nama = models.CharField(max_length=150)
    deskripsi = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Marker utama
    qr_marker_text = models.CharField(max_length=32, null=True, blank=True)
    ttd_marker_text = models.CharField(max_length=32, null=True, blank=True)

    stamp_mode = models.CharField(
        max_length=16, null=True, blank=True,
        choices=[("marker", "Marker"), ("all_markers", "All Markers")]
    )

    # optional override ukuran
    qr_width = models.IntegerField(null=True, blank=True)
    qr_height = models.IntegerField(null=True, blank=True)
    qr_x = models.IntegerField(null=True, blank=True)
    qr_y = models.IntegerField(null=True, blank=True)
    ttd_width = models.IntegerField(null=True, blank=True)
    ttd_height = models.IntegerField(null=True, blank=True)

    # ===== BARU: specimen =====
    specimen_mode = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        choices=[
            ("upload", "Upload"),
            ("generated", "Generated"),
        ],
    )

    specimen_width = models.IntegerField(null=True, blank=True)
    specimen_height = models.IntegerField(null=True, blank=True)
    specimen_bg_color = models.CharField(max_length=16, null=True, blank=True, default="#d9d9d9")
    specimen_border_color = models.CharField(max_length=16, null=True, blank=True, default="#000000")

    class Meta:
        db_table = "surat_template"
        verbose_name = "Template Surat"
        verbose_name_plural = "Template Surat"

    def __str__(self):
        return self.nama


class SuratTemplateSpecimenSlot(models.Model):
    template = models.ForeignKey(
        "SuratTemplate",
        on_delete=models.CASCADE,
        related_name="specimen_slots",
        db_column="template_id",
    )

    urutan_signer = models.PositiveIntegerField(
        help_text="Urutan penandatangan/specimen. 1 = signer pertama, 2 = signer kedua, dst."
    )

    nama_slot = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Nama bebas untuk memudahkan admin. Contoh: Penandatangan Utama / Mengetahui"
    )

    # mode penempatan
    placement_type = models.CharField(
        max_length=16,
        choices=[
            ("marker", "Marker"),
            ("pointer", "Pointer Text"),
            ("fallback", "Fallback Koordinat"),
        ],
        default="marker",
    )

    # marker slot spesimen
    marker_text = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Contoh: [SPESIMEN1], [SPESIMEN2]"
    )

    # pointer text
    pointer_text = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text='Contoh: "Hormat kami," atau "Mengetahui."'
    )

    pointer_mode = models.CharField(
        max_length=16,
        choices=[
            ("below", "Below"),
            ("above", "Above"),
            ("left", "Left"),
            ("right", "Right"),
        ],
        default="below",
    )

    offset_x = models.IntegerField(default=0)
    offset_y = models.IntegerField(default=0)

    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    fallback_page = models.IntegerField(
        null=True,
        blank=True,
        help_text="0 atau kosong = halaman terakhir"
    )
    fallback_x = models.IntegerField(null=True, blank=True)
    fallback_y = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "surat_template_specimen_slot"
        ordering = ["template_id", "urutan_signer"]
        unique_together = ("template", "urutan_signer")

    def __str__(self):
        return f"{self.template.nama} - signer #{self.urutan_signer}"


class Surat(models.Model):
    id_surat = models.BigIntegerField(primary_key=True)
    nomor_surat = models.CharField(max_length=128, null=True, blank=True)
    judul_surat = models.CharField(max_length=512, null=True, blank=True)
    tujuan_surat = models.CharField(max_length=512, null=True, blank=True)

    instansi_ref = models.ForeignKey(
        "core.RefInstansi",
        to_field="id",
        db_column="instansi_kode",   # pakai kolom existing
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="surat_set",
        db_constraint=False,
        verbose_name="Instansi",
    )

    file_surat = models.FileField(
        upload_to=surat_pdf_upload_to,
        null=True,
        blank=True,
        validators=[pdf_extension_validator, validate_pdf_magic, validate_max_10mb],
        help_text="Upload PDF. Disimpan ke MinIO: surat/YYYY/MM/DD/ (private, pakai presigned URL).",
    )

    created_by = models.ForeignKey(
        "core.MstDataPegawai",
        to_field="id",
        db_column="created_by_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="surat_created_set",
        db_constraint=False,
        verbose_name="Dibuat oleh",
    )
    create_date = models.DateTimeField(null=True, blank=True)

    class FinishStatus(models.IntegerChoices):
        ON_PROCESS = 1, "On Process"
        PENDING = 2, "Pending"
        FINISH = 3, "Finish"

    is_finish = models.IntegerField(default=1, null=True, blank=True, choices=FinishStatus.choices)
    date_finish = models.DateTimeField(null=True, blank=True)
    show_date = models.DateTimeField(null=True, blank=True)
    id_dokumen = models.CharField(max_length=100, null=True, blank=True)
    file_unsigned = models.FileField(
        upload_to=surat_pdf_upload_to,
        null=True, blank=True,
        help_text="PDF hasil stamping (QR/logo/(optional) spesimen), belum TTE cryptographic."
    )

    file_signed = models.FileField(
        upload_to=surat_pdf_upload_to,
        null=True, blank=True,
        help_text="PDF final setelah TTE cryptographic."
    )

    file_surat_sha256 = models.CharField(max_length=64, null=True, blank=True)
    file_unsigned_sha256 = models.CharField(max_length=64, null=True, blank=True)

    stamp_last_at = models.DateTimeField(null=True, blank=True)
    stamp_version = models.IntegerField(default=1)

    template_ref = models.ForeignKey(
        "core.SuratTemplate",
        to_field="id_template",
        db_column="template_id",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="surat_set",
        db_constraint=False,
        verbose_name="Template Surat",
    )

    class Meta:
        db_table = "surat"
        verbose_name = "Surat"
        verbose_name_plural = "Surat"

    def __str__(self):
        return str(self.nomor_surat or self.id_surat)


class SuratFinish(models.Model):
    id = models.AutoField(primary_key=True) 
    finish = models.CharField(max_length=100, null=True, blank=True) 

    class Meta: 
        db_table = "surat_finish" 
        verbose_name = "Surat Finish Ref" 
        verbose_name_plural = "Surat Finish Ref" 

    def __str__(self): 
        return self.finish or f"Surat Finish #{self.id}"


class SuratMsg(models.Model):
    id_msg = models.AutoField(primary_key=True)
    id_surat = models.CharField(max_length=32, null=True, blank=True)
    msg_isi = models.TextField(null=True, blank=True)
    msg_date = models.DateTimeField(null=True, blank=True)
    msg_create = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = "surat_msg"
        verbose_name = "Surat Message"
        verbose_name_plural = "Surat Message"


class SuratSignStatus(models.Model):
    id_status = models.AutoField(primary_key=True)
    nama_status = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = "surat_sign_status"
        verbose_name = "Sign Status"
        verbose_name_plural = "Sign Status"

    def __str__(self):
        return self.nama_status or f"Sign Status #{self.id_status}"


class SuratSignType(models.Model):
    id_sign = models.AutoField(primary_key=True)
    nama_sign = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = "surat_sign_type"
        verbose_name = "Sign Type"
        verbose_name_plural = "Sign Type"

    def __str__(self):
        return self.nama_sign or f"Sign Type #{self.id_sign}"


class Suratm(models.Model):
    id_surat = models.BigIntegerField(primary_key=True)
    judul_surat = models.CharField(max_length=255, null=True, blank=True)
    perihal = models.CharField(max_length=255, null=True, blank=True)
    instansi = models.CharField(max_length=255, null=True, blank=True)
    instansi_kode = models.CharField(max_length=10, null=True, blank=True)
    nip_paraf = models.CharField(max_length=18, null=True, blank=True)
    nama_paraf = models.CharField(max_length=255, null=True, blank=True)
    nip_ttd = models.CharField(max_length=18, null=True, blank=True)
    nama_ttd = models.CharField(max_length=255, null=True, blank=True)
    id_tmp = models.IntegerField(null=True, blank=True)
    is_finish = models.IntegerField(default=1, null=True, blank=True)
    nik = models.CharField(max_length=255, null=True, blank=True)
    unixchr = models.CharField(max_length=255, null=True, blank=True)
    date_finish = models.DateTimeField(null=True, blank=True)
    show_date = models.DateTimeField(null=True, blank=True)
    create_by = models.CharField(max_length=24, null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    paraf_date = models.DateTimeField(null=True, blank=True)
    ttd_date = models.DateTimeField(null=True, blank=True)
    create_name = models.CharField(max_length=255, null=True, blank=True)
    jabatan_ttd = models.CharField(max_length=255, null=True, blank=True)
    jabatan_paraf = models.CharField(max_length=255, null=True, blank=True)
    zip_file = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "suratm"
        verbose_name = "Surat (Master/Workflow)"
        verbose_name_plural = "Surat (Master/Workflow)"


class SuratmDet(models.Model):
    id_tmp_det = models.AutoField(primary_key=True)
    id_surat = models.CharField(max_length=255, null=True, blank=True)
    file_surat = models.CharField(max_length=64, null=True, blank=True)
    f1 = models.TextField(null=True, blank=True)
    f2 = models.TextField(null=True, blank=True)
    f3 = models.TextField(null=True, blank=True)
    f4 = models.TextField(null=True, blank=True)
    f5 = models.TextField(null=True, blank=True)
    f6 = models.TextField(null=True, blank=True)
    f7 = models.TextField(null=True, blank=True)
    f8 = models.TextField(null=True, blank=True)
    f9 = models.TextField(null=True, blank=True)
    f10 = models.TextField(null=True, blank=True)
    f11 = models.TextField(null=True, blank=True)
    f12 = models.TextField(null=True, blank=True)
    f13 = models.TextField(null=True, blank=True)
    f14 = models.TextField(null=True, blank=True)
    f15 = models.TextField(null=True, blank=True)
    f16 = models.TextField(null=True, blank=True)
    f17 = models.TextField(null=True, blank=True)
    f18 = models.TextField(null=True, blank=True)
    f19 = models.TextField(null=True, blank=True)
    f20 = models.TextField(null=True, blank=True)
    status = models.IntegerField(default=1, null=True, blank=True)

    class Meta:
        db_table = "suratm_det"
        verbose_name = "Surat Detail"
        verbose_name_plural = "Surat Detail"


class SuratmDetCopy(models.Model):
    id_tmp_det = models.AutoField(primary_key=True)
    id_surat = models.CharField(max_length=255, null=True, blank=True)
    file_surat = models.CharField(max_length=64, null=True, blank=True)
    f1 = models.TextField(null=True, blank=True)
    f2 = models.TextField(null=True, blank=True)
    f3 = models.TextField(null=True, blank=True)
    f4 = models.TextField(null=True, blank=True)
    f5 = models.TextField(null=True, blank=True)
    f6 = models.TextField(null=True, blank=True)
    f7 = models.TextField(null=True, blank=True)
    f8 = models.TextField(null=True, blank=True)
    f9 = models.TextField(null=True, blank=True)
    f10 = models.TextField(null=True, blank=True)
    f11 = models.TextField(null=True, blank=True)
    f12 = models.TextField(null=True, blank=True)
    f13 = models.TextField(null=True, blank=True)
    f14 = models.TextField(null=True, blank=True)
    f15 = models.TextField(null=True, blank=True)
    f16 = models.TextField(null=True, blank=True)
    f17 = models.TextField(null=True, blank=True)
    f18 = models.TextField(null=True, blank=True)
    f19 = models.TextField(null=True, blank=True)
    f20 = models.TextField(null=True, blank=True)
    status = models.IntegerField(default=1, null=True, blank=True)

    class Meta:
        db_table = "suratm_det_copy"
        verbose_name = "Surat Detail (Copy)"
        verbose_name_plural = "Surat Detail (Copy)"


class TelegramNotif(models.Model):
    tn_id = models.BigAutoField(primary_key=True)

    pegawai = models.ForeignKey(
        "core.MstDataPegawai",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="telegram_notif_set",
        db_column="pegawai_id",
    )

    tn_chat_id = models.CharField(max_length=100, null=True, blank=True)
    tn_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "telegram_notif"
        unique_together = (("pegawai", "tn_chat_id"),)
        verbose_name = "Telegram Notif"
        verbose_name_plural = "Telegram Notif"



class TmpSrtDet(models.Model):
    id_tmp = models.AutoField(primary_key=True)
    id_req = models.CharField(max_length=255, null=True, blank=True)
    val = models.TextField(null=True, blank=True)
    id_ref_template = models.IntegerField(null=True, blank=True)
    id_tr = models.BigIntegerField(null=True, blank=True)
    row_seq = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "tmp_srt_det"
        verbose_name = "Tmp Surat Detail"
        verbose_name_plural = "Tmp Surat Detail"


class TmpSrtFile(models.Model):
    id_srt_file = models.AutoField(primary_key=True)
    id_tr = models.BigIntegerField(null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "tmp_srt_file"
        verbose_name = "Tmp Surat File"
        verbose_name_plural = "Tmp Surat File"


class TteInstansi(models.Model):
    id = models.BigAutoField(primary_key=True)
    tins_nama = models.CharField(max_length=100, null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tte_instansi"
        verbose_name = "TTE Instansi"
        verbose_name_plural = "TTE Instansi"

    def __str__(self):
        return self.tins_nama or f"Instansi #{self.id}"


class TteJabatan(models.Model):
    id = models.BigAutoField(primary_key=True)
    tjab_nama = models.CharField(max_length=100, null=True, blank=True)
    tjab_parent_jabatan = models.BigIntegerField(null=True, blank=True)
    tjab_instansi = models.ForeignKey(
        TteInstansi,
        to_field="id",
        db_column="tjab_instansi",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="jabatan_set",
    )
    created_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tte_jabatan"
        verbose_name = "TTE Jabatan"
        verbose_name_plural = "TTE Jabatan"

    def __str__(self):
        return self.tjab_nama or f"Jabatan #{self.id}"


class MstDataPegawai(models.Model):
    id = models.BigAutoField(primary_key=True)

    nip = EncryptedTextField(null=True, blank=True, db_column="nip_enc")
    nik = EncryptedTextField(null=True, blank=True, db_column="nik_enc")
    nama_lengkap = EncryptedTextField(null=True, blank=True, db_column="nama_lengkap_enc")

    nip_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    nik_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    nama_lengkap_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    tempat_lahir = models.CharField(max_length=50, null=True, blank=True)
    tgl_lahir = models.DateField(null=True, blank=True)
    golongan = models.CharField(max_length=5, null=True, blank=True)
    eselon = models.CharField(max_length=5, null=True, blank=True)
    id_instansi = models.ForeignKey(
        RefInstansi,
        db_column="id_instansi",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="pegawai_set",
    )
    id_jabatan = models.ForeignKey(
        MstJabatan,
        to_field="id_jabatan",
        db_column="id_jabatan",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="pegawai_set",
    )
    pendidikan = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    keterangan = models.CharField(max_length=100, null=True, blank=True)
    createdby = models.CharField(max_length=30, null=True, blank=True)
    createddate = models.DateTimeField(null=True, blank=True)
    updatedby = models.CharField(max_length=30, null=True, blank=True)
    updateddate = models.DateTimeField(null=True, blank=True)
    # Spesimen PARAF (opsional)
    specimen_paraf = models.FileField(
        upload_to=specimen_upload_to,
        null=True, blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg"])],
        help_text="File spesimen paraf (PNG disarankan transparan). Disimpan di MinIO."
    )

    # Spesimen TTD basah (opsional)
    specimen_ttd = models.FileField(
        upload_to=specimen_upload_to,
        null=True, blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg"])],
        help_text="File spesimen tanda tangan (PNG disarankan transparan). Disimpan di MinIO."
    )

    specimen_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mst_datapegawai"
        verbose_name = "Data Pegawai"
        verbose_name_plural = "Data Pegawai"
    
    def save(self, *args, **kwargs):
        self.nip_hash = hash_lookup(self.nip) if self.nip else None
        self.nik_hash = hash_lookup(self.nik) if self.nik else None
        self.nama_lengkap_hash = hash_lookup(self.nama_lengkap) if self.nama_lengkap else None
        super().save(*args, **kwargs)

    def __str__(self):
        nip = (self.nip or "").strip()
        nama = (self.nama_lengkap or "").strip()
        nip_mask = (nip[:3] + "***" + nip[-3:]) if len(nip) >= 6 else (nip or "-")
        nama_mask = (nama[:2] + "***") if len(nama) >= 2 else (nama or "-")
        return f"{nip_mask} - {nama_mask}"

    def display_name(self, request=None):
        nip = (self.nip or "").strip()
        nama = (self.nama_lengkap or "").strip()

        if request and request.user.is_superuser:
            return f"{nip} - {nama}"

        nip_mask = (nip[:3] + "***" + nip[-3:]) if len(nip) >= 6 else (nip or "-")
        nama_mask = (nama[:2] + "***") if len(nama) >= 2 else (nama or "-")

        return f"{nip_mask} - {nama_mask}"


class SuratTahapan(models.Model):
    id_tahapan = models.AutoField(primary_key=True)
    surat = models.ForeignKey(
        "core.Surat",
        db_column="id_surat",
        on_delete=models.CASCADE,
        related_name="tahapan_set",
    )

    seq_tahapan = models.IntegerField(null=True, blank=True)

    pejabat = models.ForeignKey(
        "core.MstDataPegawai",
        to_field="id",
        db_column="pejabat_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="surat_tahapan_set",
        db_constraint=False,
    )

    sign_type_ref = models.ForeignKey(
        "core.SuratSignType",
        to_field="id_sign",
        db_column="sign_type",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tahapan_set",
        db_constraint=False,
    )

    sign_status_ref = models.ForeignKey(
        "core.SuratSignStatus",
        to_field="id_status",
        db_column="sign_status",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tahapan_set",
        db_constraint=False,
    )

    instansi_ref = models.ForeignKey(
        "core.RefInstansi",
        to_field="id",
        db_column="instansi_kode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="surat_tahapan_set",
        db_constraint=False,
        verbose_name="Instansi",
    )

    pejabat_jabatan = models.CharField(max_length=256, null=True, blank=True)
    sign_date = models.DateTimeField(null=True, blank=True)

    # ==========================
    # AUDITABLE MULTI-TTE FIELDS
    # ==========================

    # File hasil tanda tangan untuk tahapan ini (bukan hanya di Surat)
    file_signed = models.FileField(
        upload_to=upload_to_tahapan_signed,
        null=True,
        blank=True,
        verbose_name="File signed (per tahapan)",
    )

    # Urutan versi signed dalam 1 surat (1..n), memudahkan audit & chain signing
    signed_version_no = models.IntegerField(null=True, blank=True)

    # Hash untuk audit integritas file (sha256 hex)
    signed_sha256 = models.CharField(max_length=64, null=True, blank=True)

    # Nama source yang ditandatangani (unsigned / signed sebelumnya) untuk audit
    signed_source = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "surat_tahapan"
        verbose_name = "Tahapan Surat"
        verbose_name_plural = "Tahapan Surat"


class TaJabatan(models.Model):
    id = models.AutoField(primary_key=True)
    nip = models.ForeignKey(
        MstDataPegawai,
        to_field="id",
        db_column="pegawai_id",
        on_delete=models.CASCADE,
        related_name="riwayat_jabatan_set",
    )
    id_jabatan = models.ForeignKey(
        MstJabatan,
        to_field="id_jabatan",
        db_column="id_jabatan",
        on_delete=models.DO_NOTHING,
        related_name="riwayat_jabatan_set",
    )
    status = models.BooleanField(default=False)
    jabatan_awal = models.DateField()
    jabatan_akhir = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ta_jabatan"
        verbose_name = "Riwayat Jabatan"
        verbose_name_plural = "Riwayat Jabatan"


class TteUser(models.Model):
    """Model untuk tabel legacy `user`. Belum dipakai sebagai auth Django."""
    id_usr = models.BigAutoField(primary_key=True)
    nama_usr = models.CharField(max_length=128, null=True, blank=True, unique=True)
    full_usr = models.CharField(max_length=128, null=True, blank=True)
    jabatan = models.CharField(max_length=256, null=True, blank=True)
    instansi = models.CharField(max_length=256, null=True, blank=True)
    email_usr = models.CharField(max_length=64, null=True, blank=True)
    tlp_usr = models.CharField(max_length=13, null=True, blank=True)
    img_usr = models.CharField(max_length=128, null=True, blank=True)
    pwd_usr = models.CharField(max_length=512, null=True, blank=True)
    role_id_usr = models.IntegerField(null=True, blank=True)
    is_active = models.IntegerField(default=0)
    date_created_usr = models.DateTimeField(null=True, blank=True)
    update_date = models.DateTimeField(null=True, blank=True)
    id_api_peg = models.CharField(max_length=64, null=True, blank=True)
    alamat = models.TextField(null=True, blank=True)
    id_api_usr = models.CharField(max_length=64, null=True, blank=True)
    pwd_is_default = models.IntegerField(default=1)
    tele_notif = models.BooleanField(null=True, blank=True)
    tele_chat_id = models.CharField(max_length=100, null=True, blank=True)
    jabatan_loc = models.ForeignKey(
        TteJabatan,
        db_column="jabatan_loc_id",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="user_set",
    )
    instansi_fk = models.ForeignKey(
        TteInstansi,
        db_column="instansi_id",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="user_set",
    )
    change_pass = models.DateTimeField(null=True, blank=True)
    reset_pass = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user"
        verbose_name = "User (Legacy)"
        verbose_name_plural = "User (Legacy)"

    def __str__(self):
        return self.nama_usr or f"User #{self.id_usr}"

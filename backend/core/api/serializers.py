from django.utils import timezone
from rest_framework import serializers
from core.models import Surat, SuratTahapan
import random
import json
from django.db import IntegrityError, transaction
from core.services.snapshot import snapshot_jabatan_from_pegawai
from core.models import MstDataPegawai, MstJabatan, SuratTemplate
from rest_framework.fields import FileField


class HTTPSFileField(FileField):
    def to_representation(self, value):
        url = super().to_representation(value)
        if url and url.startswith("http://"):
            return url.replace("http://", "https://")
        return url

def generate_id_surat():
    # format: YYMMDDHHMMSS + 4 digit random => 12 + 4 = 16 digit
    now = timezone.localtime()
    prefix = now.strftime("%y%m%d%H%M%S")
    suffix = f"{random.randint(0, 9999):04d}"
    return int(prefix + suffix)

# class SuratTahapanSerializer(serializers.ModelSerializer):
#     pejabat_nama = serializers.SerializerMethodField()
#     pejabat_nip = serializers.SerializerMethodField()
#     sign_type_display = serializers.SerializerMethodField()
#     sign_status_display = serializers.SerializerMethodField()
#     instansi_display = serializers.SerializerMethodField()

#     class Meta:
#         model = SuratTahapan
#         fields = [
#             "id_tahapan", "surat", "seq_tahapan",
#             "pejabat", "pejabat_nip", "pejabat_nama", "pejabat_jabatan",
#             "instansi_ref", "instansi_display",
#             "sign_type_ref", "sign_type_display",
#             "sign_status_ref", "sign_status_display",
#             "sign_date",
#         ]
#         read_only_fields = ["id_tahapan", "surat", "sign_date"]

#     def get_pejabat_nama(self, obj):
#         return obj.pejabat.nama_lengkap if obj.pejabat else None

#     def get_pejabat_nip(self, obj):
#         return obj.pejabat.nip if obj.pejabat else None

#     def get_instansi_display(self, obj):
#         i = obj.instansi_ref
#         return {"id": i.id, "nama": i.nama} if i else None

#     def get_sign_type_display(self, obj):
#         t = obj.sign_type_ref
#         return {"id_sign": t.id_sign, "nama": t.nama_sign} if t else None

#     def get_sign_status_display(self, obj):
#         s = obj.sign_status_ref
#         # sesuaikan field nama status di model kamu:
#         return {"id_status": s.id_status, "nama": getattr(s, "nama_status", None) or str(s)} if s else None

class SuratTahapanSerializer(serializers.ModelSerializer):
    pejabat_nama = serializers.SerializerMethodField()
    pejabat_nip = serializers.SerializerMethodField()
    sign_type_display = serializers.SerializerMethodField()
    sign_status_display = serializers.SerializerMethodField()
    instansi_display = serializers.SerializerMethodField()

    file_signed_url = serializers.SerializerMethodField()

    class Meta:
        model = SuratTahapan
        fields = [
            "id_tahapan", "surat", "seq_tahapan",
            "pejabat", "pejabat_nip", "pejabat_nama", "pejabat_jabatan",
            "instansi_ref", "instansi_display",
            "sign_type_ref", "sign_type_display",
            "sign_status_ref", "sign_status_display",
            "sign_date",

            # === audit multi-TTE ===
            "file_signed", "file_signed_url",
            "signed_version_no", "signed_sha256", "signed_source",
        ]
        read_only_fields = [
            "id_tahapan", "surat", "sign_date",
            "file_signed", "file_signed_url",
            "signed_version_no", "signed_sha256", "signed_source",
        ]

    def get_file_signed_url(self, obj):
        f = getattr(obj, "file_signed", None)
        if not f:
            return None
        try:
            return f.url
        except Exception:
            return None

    def get_pejabat_nama(self, obj):
        return obj.pejabat.nama_lengkap if obj.pejabat else None

    def get_pejabat_nip(self, obj):
        return obj.pejabat.nip if obj.pejabat else None

    def get_instansi_display(self, obj):
        i = obj.instansi_ref
        return {"id": i.id, "nama": i.nama} if i else None

    def get_sign_type_display(self, obj):
        t = obj.sign_type_ref
        return {"id_sign": t.id_sign, "nama": t.nama_sign} if t else None

    def get_sign_status_display(self, obj):
        s = obj.sign_status_ref
        # sesuaikan field nama status di model kamu:
        return {"id_status": s.id_status, "nama": getattr(s, "nama_status", None) or str(s)} if s else None


class SuratListSerializer(serializers.ModelSerializer):
    instansi_nama = serializers.SerializerMethodField()
    created_by_nip = serializers.SerializerMethodField()
    created_by_nama = serializers.SerializerMethodField()
    file_surat_url = serializers.SerializerMethodField()
    current_tahapan = serializers.SerializerMethodField()
    file_unsigned_url = serializers.SerializerMethodField()
    file_signed_url = serializers.SerializerMethodField()

    class Meta:
        model = Surat
        fields = [
            "id_surat",
            "nomor_surat",
            "judul_surat",
            "tujuan_surat",
            "instansi_ref",
            "instansi_nama",
            "create_date",
            "is_finish",
            "date_finish",
            "created_by_nip",
            "created_by_nama",
            "file_surat_url",
            "file_unsigned_url",
            "file_signed_url",
            "current_tahapan",
        ]

    def get_instansi_nama(self, obj):
        i = obj.instansi_ref
        return getattr(i, "nama", None) if i else None

    def get_created_by_nip(self, obj):
        cb = obj.created_by
        return getattr(cb, "nip", None) if cb else None

    def get_created_by_nama(self, obj):
        cb = obj.created_by
        return getattr(cb, "nama_lengkap", None) if cb else None

    def get_file_surat_url(self, obj):
        f = obj.file_surat
        if not f:
            return None
        try:
            return f.url  # presigned (kalau media private)
        except Exception:
            return None
    
    def get_file_unsigned_url(self, obj):
        f = getattr(obj, "file_unsigned", None)
        if not f:
            return None
        try:
            return f.url
        except Exception:
            return None

    def get_file_signed_url(self, obj):
        f = getattr(obj, "file_signed", None)
        if not f:
            return None
        try:
            return f.url
        except Exception:
            return None

    def get_current_tahapan(self, obj):
        # default ambil tahapan paling awal (atau paling “aktif” jika kamu punya rule lain).
        qs = obj.tahapan_set.all().order_by("seq_tahapan", "id_tahapan")
        t = qs.first()
        if not t:
            return None

        pejabat_nip = getattr(t.pejabat, "nip", None) if t.pejabat else None
        pejabat_nama = (
            getattr(t.pejabat, "nama_lengkap", None) if t.pejabat else getattr(t, "pejabat_nama", None)
        )

        return {
            "id_tahapan": t.id_tahapan,
            "seq_tahapan": t.seq_tahapan,
            "pejabat_nip": pejabat_nip,
            "pejabat_nama": pejabat_nama,
            "sign_status": getattr(t.sign_status_ref, "id_status", None) if t.sign_status_ref else None,
        }
    


class SuratDetailSerializer(serializers.ModelSerializer):
    instansi_nama = serializers.SerializerMethodField()
    created_by_nip = serializers.SerializerMethodField()
    created_by_nama = serializers.SerializerMethodField()
    file_surat = HTTPSFileField()
    file_surat_url = serializers.SerializerMethodField()
    file_unsigned_url = serializers.SerializerMethodField()
    file_signed_url = serializers.SerializerMethodField()
    tahapan = SuratTahapanSerializer(source="tahapan_set", many=True, read_only=True)

    class Meta:
        model = Surat
        fields = [
            "id_surat",
            "nomor_surat",
            "judul_surat",
            "tujuan_surat",
            "instansi_ref",
            "instansi_nama",
            "file_surat",
            "file_surat_url",
            "file_unsigned_url",
            "file_signed_url",
            "created_by",
            "created_by_nip",
            "created_by_nama",
            "create_date",
            "is_finish",
            "date_finish",
            "show_date",
            "id_dokumen",
            "tahapan",
        ]
        read_only_fields = ["id_surat", "created_by", "create_date", "file_surat"]

    def get_instansi_nama(self, obj):
        i = obj.instansi_ref
        return getattr(i, "nama", None) if i else None

    def get_created_by_nip(self, obj):
        cb = obj.created_by
        return getattr(cb, "nip", None) if cb else None

    def get_created_by_nama(self, obj):
        cb = obj.created_by
        return getattr(cb, "nama_lengkap", None) if cb else None

    def get_file_surat_url(self, obj):
        f = obj.file_surat
        if not f:
            return None
        return f.url

    def get_file_unsigned_url(self, obj):
        f = getattr(obj, "file_unsigned", None)
        if not f:
            return None
        try:
            return f.url
        except Exception:
            return None

    def get_file_signed_url(self, obj):
        f = getattr(obj, "file_signed", None)
        if not f:
            return None
        try:
            return f.url
        except Exception:
            return None


class SuratCreateSerializer(serializers.ModelSerializer):
    template_ref = serializers.PrimaryKeyRelatedField(
        queryset=SuratTemplate.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    class Meta:
        model = Surat
        fields = ["nomor_surat", "judul_surat", "tujuan_surat", "instansi_ref", "template_ref"]

    def create(self, validated_data):
        request = self.context["request"]
        peg = getattr(request.user, "pegawai", None)

        # created_by adalah FK ke mst_datapegawai (PK=id)
        validated_data["created_by"] = peg
        validated_data["create_date"] = timezone.now()
        # is_finish default sudah 1 (On Process)
        return super().create(validated_data)


class SuratUploadPdfSerializer(serializers.Serializer):
    file_surat = serializers.FileField()


class SuratCreateWithPdfAndTahapanSerializer(serializers.ModelSerializer):
    file_surat = serializers.FileField(required=True)
    tahapan = serializers.CharField(required=False)
    template_ref = serializers.PrimaryKeyRelatedField(
        queryset=SuratTemplate.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Surat
        fields = [
            "nomor_surat",
            "judul_surat",
            "tujuan_surat",
            "instansi_ref",
            "file_surat",
            "tahapan",
            "template_ref",
        ]

    def validate_tahapan(self, value):
        try:
            data = json.loads(value)
        except Exception:
            raise serializers.ValidationError("Format tahapan harus JSON")

        if not isinstance(data, list) or not data:
            raise serializers.ValidationError("Tahapan wajib berupa list dan tidak boleh kosong")

        return data

    def create(self, validated_data):
        request = self.context["request"]
        peg = request.user.pegawai

        file_obj = validated_data.pop("file_surat")
        tahapan_list = validated_data.pop("tahapan", [])

        with transaction.atomic():
            surat = Surat.objects.create(
                id_surat=generate_id_surat(),
                created_by=peg,
                create_date=timezone.now(),
                **validated_data
            )

            surat.file_surat = file_obj
            surat.save(update_fields=["file_surat"])

            # ===== validasi uploader =====
            uploader = [t for t in tahapan_list if t.get("sign_type") == 3]
            if not uploader:
                raise serializers.ValidationError("Tahapan uploader (sign_type=3) wajib ada")

            if uploader[0]["pegawai_id"] != peg.id:
                raise serializers.ValidationError("Uploader harus pegawai yang login")

            # ===== create tahapan =====
            for t in tahapan_list:
                if int(t["sign_type"]) == 3:  # pembuat surat
                    sign_status_ref_id = 2
                    sign_date = timezone.now()
                else:
                    sign_status_ref_id = 1
                    sign_date = None

                pejabat_obj = MstDataPegawai.objects.filter(
                    id=t["pegawai_id"]
                ).select_related("id_jabatan").first()

                jabatan_snapshot = snapshot_jabatan_from_pegawai(pejabat_obj)

                SuratTahapan.objects.create(
                    surat=surat,
                    seq_tahapan=t["seq"],
                    pejabat_id=t["pegawai_id"],
                    instansi_ref=surat.instansi_ref,
                    sign_type_ref_id=t["sign_type"],
                    sign_status_ref_id=sign_status_ref_id,
                    sign_date=sign_date,
                    pejabat_jabatan=jabatan_snapshot,
                )

            return surat
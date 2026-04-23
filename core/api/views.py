from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from django.conf import settings

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import base64
import os
import tempfile
import requests

from core.models import Surat, SuratTahapan, LogBsre, Setting
from core.api.permissions import IsSuratOwnerOrStaff
from core.api.serializers import (
    SuratListSerializer, SuratDetailSerializer, SuratCreateSerializer,
    SuratUploadPdfSerializer, SuratTahapanSerializer, SuratCreateWithPdfAndTahapanSerializer
)
from core.services.surat_paraf import action_paraf
from core.utils.pdf_stamp import stamp_bsre_footnote_each_page_if_empty
import hashlib
from django.core.files.base import ContentFile


# === Mapping sesuai data DB kamu ===
SIGN_TYPE_PARAF = 1
SIGN_TYPE_TTD = 2
SIGN_TYPE_UPLOADER = 3

SIGN_STATUS_BELUM = 1
SIGN_STATUS_SUDAH = 2
SIGN_STATUS_MEMBUAT_SURAT = 3
SIGN_STATUS_PENDING = 4

BSRE_FOOTNOTE_TEXT = (
    "Dokumen ini telah ditandatangani secara elektronik menggunakan sertifikat elektronik yang\n"
    "diterbitkan oleh Balai Besar Sertifikasi Elektronik (BSrE) Badan Siber dan Sandi Negara"
)


class SuratViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSuratOwnerOrStaff]
    lookup_field = "id_surat"
    queryset = Surat.objects.all().order_by("-id_surat")

    def get_queryset(self):
        qs = super().get_queryset().order_by("-id_surat")

        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs

        peg = getattr(user, "pegawai", None)
        if not peg:
            return qs.none()

        peg_id = peg.id

        involved_tahapan = SuratTahapan.objects.filter(
            surat_id=OuterRef("id_surat"),
            pejabat_id=peg_id,
        )

        qs = qs.annotate(_involved=Exists(involved_tahapan)).filter(
            Q(created_by_id=peg_id) | Q(_involved=True)
        )

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SuratListSerializer
        if self.action == "create":
            return SuratCreateSerializer
        if self.action == "upload_pdf":
            return SuratUploadPdfSerializer
        if self.action == "create_with_pdf":
            return SuratCreateWithPdfAndTahapanSerializer
        return SuratDetailSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(
        detail=False,
        methods=["post"],
        url_path="create-with-pdf",
        url_name="create-with-pdf",
    )
    def create_with_pdf(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            surat = serializer.save()

        return Response(SuratDetailSerializer(surat).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="upload-pdf")
    def upload_pdf(self, request, id_surat=None):
        surat = self.get_object()
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        surat.file_surat = ser.validated_data["file_surat"]
        surat.save(update_fields=["file_surat"])
        return Response({
            "id_surat": surat.id_surat,
            "file_surat": surat.file_surat.name,
            "file_surat_url": surat.file_surat.url,
        }, status=200)

    @action(detail=True, methods=["get"], url_path="file-url")
    def file_url(self, request, id_surat=None):
        surat = self.get_object()
        if not surat.file_surat:
            return Response({"detail": "Belum ada file_surat."}, status=404)
        return Response({"url": surat.file_surat.url})

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, id_surat=None):
        surat = self.get_object()

        if not surat.file_surat:
            return Response({"detail": "Upload file PDF dulu sebelum submit."}, status=400)

        if surat.show_date is None:
            surat.show_date = timezone.now()
            surat.save(update_fields=["show_date"])

        # set tahapan pertama menjadi PENDING jika masih BELUM
        first = surat.tahapan_set.order_by("seq_tahapan", "id_tahapan").first()
        if first and first.sign_status_ref_id == SIGN_STATUS_BELUM:
            first.sign_status_ref_id = SIGN_STATUS_PENDING
            first.save(update_fields=["sign_status_ref_id"])

        return Response({"detail": "Surat disubmit."}, status=200)

    @action(detail=True, methods=["get", "post"], url_path="tahapan")
    def tahapan(self, request, id_surat=None):
        surat = self.get_object()

        if request.method.lower() == "get":
            qs = surat.tahapan_set.all().order_by("seq_tahapan", "id_tahapan")
            return Response(SuratTahapanSerializer(qs, many=True).data)

        ser = SuratTahapanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            obj = ser.save(surat=surat)
        return Response(SuratTahapanSerializer(obj).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Hapus surat: tidak boleh jika ada tahapan PARAF yang sudah selesai.
        """
        surat = self.get_object()

        blocked = SuratTahapan.objects.filter(
            surat=surat,
            sign_type_ref_id=SIGN_TYPE_PARAF,
        ).filter(
            Q(sign_status_ref_id=SIGN_STATUS_SUDAH) | Q(sign_date__isnull=False)
        ).exists()

        if blocked:
            return Response(
                {"detail": "Tidak boleh hapus surat: ada tahapan paraf yang sudah selesai."},
                status=400
            )

        return super().destroy(request, *args, **kwargs)


class SuratTahapanViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "id_tahapan"
    queryset = SuratTahapan.objects.select_related(
        "surat", "pejabat", "sign_type_ref", "sign_status_ref", "instansi_ref"
    )

    @action(detail=True, methods=["post"], url_path="paraf")
    def paraf(self, request, id_tahapan=None, *args, **kwargs):
        """
        POST /api/v1/core/tahapan/{id_tahapan}/paraf/
        - verify_base_url diambil dari Setting.verify_base_url
        - handle multi-paraf via paraf_index (urutan tahapan paraf)
        """
        t = self.get_object()

        peg = getattr(request.user, "pegawai", None)
        if not peg:
            return Response({"detail": "User tidak terhubung ke data pegawai."}, status=403)

        if t.pejabat_id != peg.id:
            return Response({"detail": "Bukan tahapan Anda."}, status=403)

        if int(t.sign_type_ref_id or 0) != SIGN_TYPE_PARAF:
            return Response({"detail": "Tahapan ini bukan PARAF."}, status=400)

        if t.sign_status_ref_id == SIGN_STATUS_SUDAH or t.sign_date is not None:
            return Response({"detail": "Tahapan paraf ini sudah selesai."}, status=400)

        setting = Setting.objects.order_by("id_set").first()
        verify_base_url = getattr(setting, "verify_base_url", None)
        if not verify_base_url:
            return Response({"detail": "verify_base_url belum diset di Setting."}, status=500)
        verify_base_url = verify_base_url.rstrip("/")

        # hitung index paraf (untuk multi-paraf)
        paraf_qs = SuratTahapan.objects.filter(
            surat=t.surat,
            sign_type_ref_id=SIGN_TYPE_PARAF
        ).order_by("seq_tahapan", "id_tahapan")
        paraf_ids = list(paraf_qs.values_list("id_tahapan", flat=True))
        paraf_index = paraf_ids.index(t.id_tahapan) if t.id_tahapan in paraf_ids else 0

        res = action_paraf(
            surat_id=t.surat_id,
            pejabat_id=peg.id,
            verify_base_url=verify_base_url,
            paraf_index=paraf_index,
            setting_id=(setting.id_set if setting else None),
        )

        # refresh surat (kalau action_paraf update file_unsigned)
        t.surat.refresh_from_db()

        return Response({
            "detail": "OK paraf.",
            "result": res,
            "surat": SuratDetailSerializer(t.surat).data
        }, status=200)

    @action(detail=True, methods=["post"], url_path="sign")
    def sign(self, request, id_tahapan=None, *args, **kwargs):
        """
        Multi-TTE / auditable:
        - input: latest signed (tahapan terakhir) jika ada, kalau belum pakai surat.file_unsigned
        - output:
            * tahapan.file_signed (audit trail per signer)
            * surat.file_signed (latest/current, kompat untuk sistem lama)
        """
        t = self.get_object()

        peg = getattr(request.user, "pegawai", None)
        if not peg:
            return Response({"detail": "User tidak terhubung ke data pegawai."}, status=403)

        if t.pejabat_id != peg.id:
            return Response({"detail": "Bukan tahapan Anda."}, status=403)

        if int(t.sign_type_ref_id or 0) != SIGN_TYPE_TTD:
            return Response({"detail": "Tahapan ini bukan TTD."}, status=400)

        if not t.surat or not t.surat.file_unsigned:
            return Response({"detail": "Surat belum memiliki file_unsigned (hasil paraf/stamp)."}, status=400)

        # jika tahapan ini sudah sign, block
        if t.sign_date is not None or int(t.sign_status_ref_id or 0) == SIGN_STATUS_SUDAH:
            return Response({"detail": "Tahapan TTD ini sudah selesai."}, status=400)

        passphrase = (request.data.get("passphrase") or "").strip()
        if not passphrase:
            return Response({"detail": "Passphrase wajib diisi."}, status=400)

        nik = getattr(peg, "nik", None)
        if not nik:
            return Response({"detail": "NIK pegawai tidak tersedia."}, status=400)

        # Enforce urutan TTD (opsional tapi sangat disarankan untuk perjanjian multi pihak)
        # Pastikan semua tahapan TTD dengan seq lebih kecil sudah selesai.
        seq = t.seq_tahapan if t.seq_tahapan is not None else 0
        prev_pending = SuratTahapan.objects.filter(
            surat=t.surat,
            sign_type_ref_id=SIGN_TYPE_TTD,
        ).filter(
            # yang seq lebih kecil (atau kalau seq null, kita treat sebagai 0)
            Q(seq_tahapan__lt=seq) | Q(seq_tahapan__isnull=True, id_tahapan__lt=t.id_tahapan)
        ).filter(
            sign_date__isnull=True
        ).exists()
        if prev_pending:
            return Response({"detail": "Masih ada tahapan TTD sebelumnya yang belum selesai."}, status=400)

        # Basic auth ke BSrE
        credential_id = settings.ESIGN["USERNAME"]
        credential_key = settings.ESIGN["PASSWORD"]
        token_string = f"{credential_id}:{credential_key}".encode("ascii")
        base64_string = base64.b64encode(token_string).decode("ascii")
        sign_url = settings.ESIGN["URL"]
        headers = {"Authorization": "Basic " + base64_string}

        tmp_ready = None

        try:
            # ==========================
            # 1) Tentukan input PDF
            # ==========================
            # Cari signed terbaru dari tahapan TTD yang sudah selesai (audit chain)
            last_signed = SuratTahapan.objects.filter(
                surat=t.surat,
                sign_type_ref_id=SIGN_TYPE_TTD,
                sign_date__isnull=False,
            ).exclude(file_signed="").exclude(file_signed__isnull=True).order_by(
                "-signed_version_no", "-sign_date", "-id_tahapan"
            ).first()

            if last_signed and last_signed.file_signed:
                src_file = last_signed.file_signed
                src_label = f"tahapan:{last_signed.id_tahapan}"
            elif t.surat.file_signed:
                # fallback kompat lama (kalau sebelumnya pernah tersimpan di surat.file_signed)
                src_file = t.surat.file_signed
                src_label = "surat:file_signed"
            else:
                src_file = t.surat.file_unsigned
                src_label = "surat:file_unsigned"

            # Read bytes dari storage (S3/MinIO/local) -> jangan pakai .path
            try:
                src_file.open("rb")
                input_bytes = src_file.read()
            finally:
                try:
                    src_file.close()
                except Exception:
                    pass

            if not input_bytes:
                return Response({"detail": "Input PDF kosong / gagal dibaca dari storage."}, status=400)

            # ==========================
            # 2) Stamp footnote BSrE
            # ==========================
            setting = Setting.objects.order_by("id_set").first()
            bsre_logo_bytes = None
            if setting and getattr(setting, "bsre_logo", None):
                try:
                    setting.bsre_logo.open("rb")
                    bsre_logo_bytes = setting.bsre_logo.read()
                except Exception:
                    bsre_logo_bytes = None
                finally:
                    try:
                        setting.bsre_logo.close()
                    except Exception:
                        pass

            pdf_ready_to_sign = stamp_bsre_footnote_each_page_if_empty(
                pdf_bytes=input_bytes,
                footnote_text=BSRE_FOOTNOTE_TEXT,
                bsre_logo_png_bytes=bsre_logo_bytes,
            )

            # ==========================
            # 3) Temp file untuk multipart upload
            # ==========================
            with tempfile.NamedTemporaryFile(prefix=f"ready_{t.surat.id_surat}_", suffix=".pdf", delete=False) as tf:
                tf.write(pdf_ready_to_sign)
                tf.flush()
                tmp_ready = tf.name

            base_name = os.path.basename(tmp_ready)

            # NOTE: kalau nanti mau posisi tanda tangan per pihak,
            # pindahkan data page/x/y/w/h ke field SuratTahapan.
            data = {
                "nik": nik,
                "passphrase": passphrase,
                "tampilan": "invisible",
                "image": "false",
                "linkQR": "",
                "page": "1",
                "width": "65",
                "height": "-40",
                "xAxis": "-3",
                "yAxis": "105",
            }

            # ==========================
            # 4) Call BSrE
            # ==========================
            with open(tmp_ready, "rb") as fh:
                files = {"file": (base_name, fh, "application/pdf")}
                resp = requests.post(
                    sign_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60,
                )

            if resp.status_code != 200:
                msg = (resp.text or "")[:500]
                LogBsre.objects.create(
                    pegawai=peg,
                    surat=t.surat,
                    file=str(getattr(src_file, "name", "")),
                    msg_log=f"BSrE error {resp.status_code}: {msg}",
                    kategori=2,
                    waktu=timezone.now(),
                )
                return Response(
                    {"detail": "Gagal sign ke BSrE", "status_code": resp.status_code},
                    status=400,
                )

            if not resp.content:
                LogBsre.objects.create(
                    pegawai=peg,
                    surat=t.surat,
                    file=str(getattr(src_file, "name", "")),
                    msg_log="BSrE mengembalikan konten kosong.",
                    kategori=2,
                    waktu=timezone.now(),
                )
                return Response({"detail": "Gagal sign: hasil dari BSrE kosong."}, status=400)

            signed_bytes = resp.content
            sha256_hex = hashlib.sha256(signed_bytes).hexdigest()

            # ==========================
            # 5) Simpan: audit per tahapan + latest ke surat
            # ==========================
            with transaction.atomic():
                # versi berikutnya
                # (ambil max dari tahapan yang sudah signed_version_no terisi)
                max_v = SuratTahapan.objects.filter(
                    surat=t.surat,
                    sign_type_ref_id=SIGN_TYPE_TTD,
                ).exclude(signed_version_no__isnull=True).order_by("-signed_version_no").values_list(
                    "signed_version_no", flat=True
                ).first()
                next_v = (int(max_v) if max_v else 0) + 1

                # simpan per tahapan (audit)
                t.signed_version_no = next_v
                t.signed_sha256 = sha256_hex
                t.signed_source = src_label

                tahapan_signed_name = f"signed/tahapan/{t.id_tahapan}/ttd_{t.id_tahapan}_v{next_v}.pdf"
                t.file_signed.save(tahapan_signed_name, ContentFile(signed_bytes), save=False)

                # update status tahapan
                t.sign_status_ref_id = SIGN_STATUS_SUDAH
                t.sign_date = timezone.now()
                t.save(update_fields=[
                    "file_signed",
                    "signed_version_no",
                    "signed_sha256",
                    "signed_source",
                    "sign_status_ref_id",
                    "sign_date",
                ])

                # update latest/current di surat (kompat lama)
                surat_signed_name = f"signed/surat_{t.surat.id_surat}_latest.pdf"
                t.surat.file_signed.save(surat_signed_name, ContentFile(signed_bytes), save=False)

                # finish surat jika semua tahapan TTD sudah sign_date
                still_pending_any = SuratTahapan.objects.filter(
                    surat=t.surat,
                ).filter(
                    Q(sign_date__isnull=True) & ~Q(sign_status_ref_id=SIGN_STATUS_SUDAH)
                ).exists()

                if not still_pending_any:
                    t.surat.is_finish = Surat.FinishStatus.FINISH  # = 2
                    t.surat.date_finish = timezone.now()
                    t.surat.save(update_fields=["file_signed", "is_finish", "date_finish"])
                else:
                    # tetap update latest file_signed saja
                    t.surat.save(update_fields=["file_signed"])

            LogBsre.objects.create(
                pegawai=peg,
                surat=t.surat,
                file=str(t.file_signed),
                msg_log=f"Sukses v{t.signed_version_no} sha256={t.signed_sha256}"[:500],
                kategori=2,
                waktu=timezone.now(),
            )

            return Response(
                {"detail": "OK signed.", "tahapan": SuratTahapanSerializer(t).data},
                status=200,
            )

        except Exception as e:
            LogBsre.objects.create(
                pegawai=peg,
                surat=t.surat,
                file=str(getattr(t.surat, "file_unsigned", "")),
                msg_log=str(e)[:500],
                kategori=2,
                waktu=timezone.now(),
            )
            return Response({"detail": str(e)}, status=500)

        finally:
            if tmp_ready:
                try:
                    if os.path.exists(tmp_ready):
                        os.remove(tmp_ready)
                except Exception:
                    pass

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, id_tahapan=None, *args, **kwargs):
        """
        Reject by staff/verifikator.
        Catatan: tabel surat_sign_status kamu belum punya status "Reject".
        Jadi di sini kita set kembali ke PENDING + log alasan (aman).
        """
        t = self.get_object()
        if not request.user.is_staff:
            return Response({"detail": "Hanya staff."}, status=403)

        alasan = (request.data.get("alasan") or "").strip()
        # set pending (atau tetap belum) - pilih pending agar jelas butuh tindakan ulang
        t.sign_status_ref_id = SIGN_STATUS_PENDING
        t.save(update_fields=["sign_status_ref_id"])

        LogBsre.objects.create(
            pegawai=getattr(request.user, "pegawai", None),
            surat=t.surat,
            file=str(getattr(t.surat, "file_unsigned", "")),
            msg_log=f"Reject: {alasan}"[:500],
            kategori=2,
            waktu=timezone.now(),
        )

        return Response({"detail": "Rejected (set pending).", "tahapan": SuratTahapanSerializer(t).data}, status=200)

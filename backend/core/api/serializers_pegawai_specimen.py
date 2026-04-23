from rest_framework import serializers
from django.utils import timezone
from core import models


class PegawaiSpecimenUpdateSerializer(serializers.ModelSerializer):
    # optional flags untuk hapus file
    delete_paraf = serializers.BooleanField(required=False, default=False)
    delete_ttd = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = models.MstDataPegawai
        fields = (
            "id",
            "specimen_paraf",
            "specimen_ttd",
            "delete_paraf",
            "delete_ttd",
            "specimen_updated_at",
        )
        read_only_fields = ("id", "specimen_updated_at")

    def validate(self, attrs):
        # Minimal: harus ada file yang diupload ATAU ada flag delete
        has_file = bool(attrs.get("specimen_paraf")) or bool(attrs.get("specimen_ttd"))
        has_delete = bool(attrs.get("delete_paraf")) or bool(attrs.get("delete_ttd"))
        if not has_file and not has_delete:
            raise serializers.ValidationError(
                "Tidak ada perubahan. Upload specimen_paraf/specimen_ttd atau set delete_paraf/delete_ttd."
            )
        return attrs

    def update(self, instance, validated_data):
        delete_paraf = validated_data.pop("delete_paraf", False)
        delete_ttd = validated_data.pop("delete_ttd", False)

        # Upload baru (kalau ada)
        if "specimen_paraf" in validated_data:
            # opsional: kalau mau hapus lama dulu biar bersih
            if instance.specimen_paraf:
                instance.specimen_paraf.delete(save=False)
            instance.specimen_paraf = validated_data["specimen_paraf"]

        if "specimen_ttd" in validated_data:
            if instance.specimen_ttd:
                instance.specimen_ttd.delete(save=False)
            instance.specimen_ttd = validated_data["specimen_ttd"]

        # Delete berdasarkan flag
        if delete_paraf and instance.specimen_paraf:
            instance.specimen_paraf.delete(save=False)
            instance.specimen_paraf = None

        if delete_ttd and instance.specimen_ttd:
            instance.specimen_ttd.delete(save=False)
            instance.specimen_ttd = None

        instance.specimen_updated_at = timezone.now()
        instance.save(update_fields=["specimen_paraf", "specimen_ttd", "specimen_updated_at"])
        return instance

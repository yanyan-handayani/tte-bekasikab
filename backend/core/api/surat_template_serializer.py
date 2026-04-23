from rest_framework import serializers
from core.models import SuratTemplate


class SuratTemplateReadonlySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuratTemplate
        fields = ("id_template", "kode", "nama")
        read_only_fields = fields

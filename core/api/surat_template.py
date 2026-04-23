from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.models import SuratTemplate
from core.api.surat_template_serializer import SuratTemplateReadonlySerializer


class SuratTemplateReadonlyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuratTemplateReadonlySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            SuratTemplate.objects
            .filter(is_active=True)
            .only("id_template", "kode", "nama")
            .order_by("kode")
        )

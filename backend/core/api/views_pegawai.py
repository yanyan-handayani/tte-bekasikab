from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from core import models
from core.api.serializers_pegawai_specimen import PegawaiSpecimenUpdateSerializer


class PegawaiViewSet(viewsets.GenericViewSet):
    queryset = models.MstDataPegawai.objects.all()
    permission_classes = [IsAuthenticated]

    @action(
        detail=True,
        methods=["PATCH", "POST"],  # PATCH recommended; POST biar fleksibel untuk client yang susah PATCH multipart
        url_path="specimen",
        parser_classes=[MultiPartParser, FormParser],
    )
    def specimen(self, request, pk=None):
        pegawai = self.get_object()

        serializer = PegawaiSpecimenUpdateSerializer(
            pegawai,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # response ringkas + URL file (kalau storage menyediakan url)
        data = {
            "id": pegawai.id,
            "specimen_paraf": request.build_absolute_uri(pegawai.specimen_paraf.url) if pegawai.specimen_paraf else None,
            "specimen_ttd": request.build_absolute_uri(pegawai.specimen_ttd.url) if pegawai.specimen_ttd else None,
            "specimen_updated_at": pegawai.specimen_updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)

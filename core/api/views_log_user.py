from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from core.models import LogUsr
from core.api.serializer_log_user import LogUsrSerializer, LogUsrCreateSerializer


class LogUsrViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.CreateModelMixin,
                    viewsets.GenericViewSet):
    """
    GET /api/core/loguseractivity/
    GET /api/core/loguseractivity/{id_log}/
    POST /api/core/loguseractivity/  (buat log)
    """
    permission_classes = [IsAuthenticated]
    queryset = LogUsr.objects.select_related("user", "pegawai").all()
    lookup_field = "id_log"

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["kategori", "user", "pegawai"]
    search_fields = ["aktivitas"]
    ordering_fields = ["waktu", "id_log", "kategori"]
    ordering = ["-waktu", "-id_log"]

    def get_serializer_class(self):
        if self.action == "create":
            return LogUsrCreateSerializer
        return LogUsrSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs

        # user biasa: hanya miliknya sendiri
        return qs.filter(user=user)

from rest_framework import serializers
from django.utils import timezone

from core.models import LogUsr


class LogUsrSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    pegawai_id = serializers.IntegerField(source="pegawai.id", read_only=True)

    class Meta:
        model = LogUsr
        fields = [
            "id_log",
            "waktu",
            "kategori",
            "aktivitas",
            "ipaddr",
            "user_id",
            "username",
            "pegawai_id",
        ]
        read_only_fields = ["id_log", "user_id", "username", "pegawai_id"]


class LogUsrCreateSerializer(serializers.ModelSerializer):
    """
    Create log:
    - user & pegawai diambil dari request.user (kalau ada relasi)
    - waktu default now()
    - ipaddr otomatis dari request (atau boleh override jika superuser)
    """
    class Meta:
        model = LogUsr
        fields = ["waktu", "kategori", "aktivitas", "ipaddr"]

    def validate(self, attrs):
        # default waktu
        if not attrs.get("waktu"):
            attrs["waktu"] = timezone.now()

        aktivitas = (attrs.get("aktivitas") or "").strip()
        if aktivitas:
            attrs["aktivitas"] = aktivitas[:256]
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # ip dari request kalau tidak diisi
        if not validated_data.get("ipaddr"):
            ip = None
            if request:
                xff = request.META.get("HTTP_X_FORWARDED_FOR")
                if xff:
                    ip = xff.split(",")[0].strip()
                else:
                    ip = request.META.get("REMOTE_ADDR")
            validated_data["ipaddr"] = ip

        obj = LogUsr(**validated_data)

        # set user kalau authenticated
        if user and getattr(user, "is_authenticated", False):
            obj.user = user
            # OPTIONAL: kalau user punya field pegawai atau relasi tertentu
            # Silakan sesuaikan dengan projectmu:
            pegawai = getattr(user, "pegawai", None)
            if pegawai:
                obj.pegawai = pegawai

        obj.save()
        return obj

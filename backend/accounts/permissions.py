from rest_framework.permissions import BasePermission


class BlockAccessUntilPasswordChanged(BasePermission):
    """
    Jika password expired / must_change_password = True,
    user hanya boleh akses endpoint tertentu sampai password diubah.
    """

    allowed_paths = {
        "/api/auth/password/change",
        "/api/auth/me",
        "/api/token/refresh",
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        # request anonim / belum login -> biarkan lewat ke permission berikutnya
        if not user or not user.is_authenticated:
            return True

        must_change = bool(getattr(user, "must_change_password", False))
        expired = bool(user.password_is_expired())

        if not (must_change or expired):
            return True

        path = request.path.rstrip("/") or "/"
        allowed = {p.rstrip("/") or "/" for p in self.allowed_paths}

        return path in allowed
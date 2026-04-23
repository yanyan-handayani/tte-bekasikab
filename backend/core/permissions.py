from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

class IsOwnerOrStaff(BasePermission):
    """
    Owner = created_by (atau pegawai pembuat) boleh edit draft miliknya.
    Staff boleh semua.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        created_by = getattr(obj, "created_by", None)
        return created_by_id_matches_user(created_by, request.user)

def created_by_id_matches_user(created_by, user):
    if not user or not user.is_authenticated:
        return False
    # created_by bisa FK ke accounts.User atau ke pegawai. Sesuaikan.
    if hasattr(created_by, "pk") and hasattr(user, "pk") and created_by.pk == user.pk:
        return True
    # kalau obj.created_by adalah pegawai:
    if hasattr(user, "pegawai") and user.pegawai and hasattr(created_by, "pk"):
        return created_by.pk == user.pegawai.pk
    return False

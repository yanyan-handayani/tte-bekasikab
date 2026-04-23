from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuratOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated

        if request.user.is_staff or request.user.is_superuser:
            return True

        peg = getattr(request.user, "pegawai", None)
        if not peg:
            return False

        cb = getattr(obj, "created_by", None)
        if not cb:
            return False

        # created_by adalah FK ke MstDataPegawai (to_field nip)
        return getattr(cb, "nip", None) == getattr(peg, "nip", None)

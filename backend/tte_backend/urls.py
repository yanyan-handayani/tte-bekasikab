from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from accounts.api import MeView, PasswordResetRequestView, PasswordResetConfirmView, PasswordChangeView
from accounts.jwt import CustomTokenObtainPairView
from accounts.api_2fa import TwoFASetupView, TwoFAEnableView, TwoFADisableView
from core.views_verifikasi import verifikasi_view, verifikasi_pdf, lihat_surat_legacy

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/password/reset/request", PasswordResetRequestView.as_view()),
    path("api/auth/password/reset/confirm", PasswordResetConfirmView.as_view()),
    path("api/auth/password/change", PasswordChangeView.as_view()),
    path("api/v1/", include("core.api.urls")),
    path("api/2fa/setup/", TwoFASetupView.as_view(), name="2fa_setup"),
    path("api/2fa/enable/", TwoFAEnableView.as_view(), name="2fa_enable"),
    path("api/2fa/disable/", TwoFADisableView.as_view(), name="2fa_disable"),
    path("verifikasi/<str:token>", verifikasi_view, name="tte_verifikasi"),
    path("verifikasi/<str:token>/pdf", verifikasi_pdf, name="tte_verifikasi_pdf"),
    path("Lihat/surat/<int:id_surat>", lihat_surat_legacy, name="tte_lihat_legacy"),
]

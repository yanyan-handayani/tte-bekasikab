from rest_framework.routers import DefaultRouter
from core.api.views import SuratViewSet, SuratTahapanViewSet
from core.api.views_pegawai import PegawaiViewSet
from core.api.surat_template import SuratTemplateReadonlyViewSet
from core.api.views_log_user import LogUsrViewSet

router = DefaultRouter()
router.register(r"core/surat", SuratViewSet, basename="core-surat")
router.register(r"core/tahapan", SuratTahapanViewSet, basename="core-tahapan")
router.register(r"pegawai", PegawaiViewSet, basename="pegawai")
router.register(r"surat-templates", SuratTemplateReadonlyViewSet, basename="surat-template")
router.register(r"loguseractivity", LogUsrViewSet, basename="loguseractivity")

urlpatterns = router.urls

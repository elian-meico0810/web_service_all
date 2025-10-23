from rest_framework.routers import DefaultRouter
from apps.scripts.api.scripts_api import ScriptsViewSet

router = DefaultRouter()

router.register(r'', ScriptsViewSet, basename='ws-sc-scripts')
urlpatterns = router.urls

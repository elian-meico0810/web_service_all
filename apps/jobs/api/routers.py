from rest_framework.routers import DefaultRouter
from apps.jobs.api.jobs_api import JobsViewSet

router = DefaultRouter()

router.register(r'', JobsViewSet, basename='ws-sc-jobs')
urlpatterns = router.urls

from django.urls import path, include
from rest_framework import routers

from . import views
from . import api

router = routers.DefaultRouter()
router.register(r'mpas', api.MPAViewSet, basename='mpa')

app_name = 'dto'
urlpatterns = [
    path('', views.index, name='index'),
    path('api/', include(router.urls)),
    path('api/mpa-zones/geojson/', api.mpa_zones_geojson, name='mpa_zones_geojson'),
    path('api/mpa/<int:mpa_id>/parameters/', api.get_available_parameters, name='available_parameters'),
    path('api/mpa/<int:mpa_id>/timeseries/<str:parameter>/', api.get_mpa_timeseries, name='mpa_timeseries'),
    path('api/mpa/latest-date/', api.get_latest_timeseries_date, name='latest_date'),
]
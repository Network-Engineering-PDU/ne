from rest_framework import routers

from rest.viewsets import PDUDataViewSet, SensorsDataViewSet, SensorsNewViewSet
from rest.sensors_scan_views import SensorsScanViewSet

api_router = routers.SimpleRouter()
api_router.register(r'pdu-data', PDUDataViewSet, basename='pdu-data')
api_router.register(r'sensors-data', SensorsDataViewSet, basename='sensors-data')
api_router.register(r'sensors-new', SensorsNewViewSet, basename='sensors-new')
api_router.register(r'sensors-scan', SensorsScanViewSet, basename='sensors-scan')

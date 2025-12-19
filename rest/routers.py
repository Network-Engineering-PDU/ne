from rest_framework import routers

from rest.viewsets import PDUDataViewSet, SensorsDataViewSet, SensorsNewViewSet

api_router = routers.SimpleRouter()
api_router.register(r'pdu-data', PDUDataViewSet, basename='pdu-data')
api_router.register(r'sensors-data', SensorsDataViewSet, basename='sensors-data')
api_router.register(r'sensors-new', SensorsNewViewSet, basename='sensors-new')

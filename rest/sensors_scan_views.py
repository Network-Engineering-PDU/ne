from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from app import minew_scanner


class SensorsScanViewSet(viewsets.ViewSet):
    """Discovery and registration for Minew MST01 / BeaconX BLE sensors."""

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        result = minew_scanner.start_scan()
        code = status.HTTP_200_OK if result.get('ok') else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({'result': 'OK' if result.get('ok') else 'ERROR', **result}, status=code)

    @action(detail=False, methods=['post'], url_path='stop')
    def stop(self, request):
        result = minew_scanner.stop_scan()
        return Response({'result': 'OK', **result})

    @action(detail=False, methods=['get'], url_path='discovered')
    def discovered(self, request):
        data = minew_scanner.get_scan_status()
        return Response(data)

    @action(detail=False, methods=['post'], url_path='confirm')
    def confirm(self, request):
        add_all = bool(request.data.get('all'))
        macs = request.data.get('macs') or []
        if not add_all and not macs:
            return Response({
                'result': 'ERROR',
                'detail': 'Provide "macs" or "all": true',
            }, status=status.HTTP_400_BAD_REQUEST)
        result = minew_scanner.confirm_sensors(macs=macs, add_all=add_all)
        return Response({'result': 'OK', **result})

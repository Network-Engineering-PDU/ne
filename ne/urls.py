from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from app import views
from rest.routers import api_router
from ne.settings import MEDIA_URL, MEDIA_ROOT, STATIC_URL, STATIC_ROOT


urlpatterns = [

    # Auth
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Admin
    path('admin/', admin.site.urls),

    # Main pages
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),

    # API router
    path('api/', include(api_router.urls)),

]


urlpatterns += i18n_patterns(
    # App (views)
    path('', views.login_user, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('inputs/', views.inputs, name='inputs'),
    path('pdu/live_inputs/', views.pdu_live_inputs, name='pdu_live_inputs'),
    path('inputs/<int:input_id>/download_last_data', views.input_download_last_data, name='input_download_last_data'),
    path('outputs/', views.outputs, name='outputs'),
    path('outputs/<int:output_id>/download_last_data', views.output_download_last_data, name='output_download_last_data'),
    path('update_limits', views.update_limits, name='update_limits'),
    path('settings/', views.settings, name='settings'),
    path('coms/', views.coms, name='coms'),
    path('hosts/', views.hosts, name='hosts'),
    path('check_new_sensor/', views.check_new_sensor, name='check_new_sensor'),
    path('sensors/', views.sensors, name='sensors'),
    path('sensors/<int:sensor_id>/update_name', views.sensor_update_name, name='sensor_update_name'),
    # path('profile/', views.profile, name='profile'),
    path('users/', views.users, name='users'),

    # prefix_default_language=True
)


urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
urlpatterns += static(STATIC_URL, document_root=STATIC_ROOT)

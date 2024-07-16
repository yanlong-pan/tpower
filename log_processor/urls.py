from django.urls import path
from .views import ProcessChargerSentLogsAPIView

urlpatterns = [
    path('api/process-charger-sent-logs', ProcessChargerSentLogsAPIView.as_view(), name='process-charger-sent-logs'),
]

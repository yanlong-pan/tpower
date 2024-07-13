from django.urls import path
from .views import DataTransferAPIView

urlpatterns = [
    path('api/data-transfer', DataTransferAPIView.as_view(), name='data-transfer'),
]

from django.urls import path
from .views import DataTransferAPIView, SubmitView

urlpatterns = [
    path('submit', SubmitView.as_view(), name='submit'),
    path('api/data-transfer', DataTransferAPIView.as_view(), name='data-transfer'),
]

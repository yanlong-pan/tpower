from rest_framework import serializers

from log_processor.models import DataTransfer

class TextSerializer(serializers.Serializer):
    text = serializers.CharField()

class DataTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataTransfer
        fields = ['vendorId', 'messageId', 'data']
from rest_framework import serializers

from log_processor.models import DataTransferRequest, SampledMeterValue

class DataTransferRequestSerializer(serializers.ModelSerializer):
    vendorId = serializers.CharField(source='vendor_id')
    messageId = serializers.CharField(source='message_id')
    data = serializers.CharField(allow_blank=True)
    class Meta:
        model = DataTransferRequest
        fields = ['charger_number', 'vendorId', 'messageId', 'data', 'raw_data']

    def create(self, validated_data):
        data_transfer_request = DataTransferRequest.objects.create(**validated_data)
        return data_transfer_request

class SampledMeterValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampledMeterValue
        fields = '__all__'

SERIALIZER_TYPES_MAP = {
    'datatransfer': DataTransferRequestSerializer,
    'metervalues': SampledMeterValueSerializer,
}
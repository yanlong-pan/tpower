from rest_framework import serializers

from log_processor.models import DataTransferRequest, Location, Measurand, Phase, ReadingContext, SampledMeterValue, UnitOfMeasure, ValueFormat

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

class SampledValueSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    value = serializers.CharField()
    context = serializers.ChoiceField(choices=[e.value for e in ReadingContext], allow_blank=True, required=False)
    format = serializers.ChoiceField(choices=[e.value for e in ValueFormat], allow_blank=True, required=False)
    measurand = serializers.ChoiceField(choices=[e.value for e in Measurand], allow_blank=True, required=False)
    phase = serializers.ChoiceField(choices=[e.value for e in Phase], allow_blank=True, required=False)
    location = serializers.ChoiceField(choices=[e.value for e in Location], allow_blank=True, required=False)
    unit = serializers.ChoiceField(choices=[e.value for e in UnitOfMeasure], allow_blank=True, required=False)

class SampledMeterValueSerializer(serializers.ModelSerializer):
    L1 = SampledValueSerializer(many=True)
    L2 = SampledValueSerializer(many=True)
    L3 = SampledValueSerializer(many=True)
    class Meta:
        model = SampledMeterValue
        fields = '__all__'

SERIALIZER_TYPES_MAP = {
    'datatransfer': DataTransferRequestSerializer,
    'metervalues': SampledMeterValueSerializer,
}
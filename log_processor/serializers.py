from rest_framework import serializers

from log_processor.models import DataTransferRequest, MeterValue, MeterValuesRequest, SampledValue

class ChargerRequestMetaClass(serializers.SerializerMetaclass):
    def __new__(cls, name, bases, attrs):
        # Determine whether it is a base class and avoid modifying the Meta of the base class
        if 'Meta' in attrs and getattr(attrs['Meta'], 'abstract', False):
            return super(ChargerRequestMetaClass, cls).__new__(cls, name, bases, attrs)

        # Automatically add 'chargerNumber' to the fields in Meta
        if 'Meta' in attrs and hasattr(attrs['Meta'], 'fields'):
            fields = list(attrs['Meta'].fields)
            fields.append('chargerNumber')
            attrs['Meta'].fields = fields
        return super(ChargerRequestMetaClass, cls).__new__(cls, name, bases, attrs)

class ChargerRequestBaseSerializer(serializers.Serializer, metaclass=ChargerRequestMetaClass):
    chargerNumber = serializers.CharField(source='charger_number')

    class Meta:
        abstract = True
        fields = ()

class DataTransferRequestSerializer(ChargerRequestBaseSerializer):
    vendorId = serializers.CharField(source='vendor_id')
    messageId = serializers.CharField(source='message_id')
    data = serializers.CharField()
    class Meta:
        model = DataTransferRequest
        fields = ['vendorId', 'messageId', 'data']

    def create(self, validated_data):
        data_transfer_request = DataTransferRequest.objects.create(**validated_data)
        return data_transfer_request

class SampledValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampledValue
        fields = '__all__'

class MeterValueSerializer(serializers.ModelSerializer):
    sampledValue = SampledValueSerializer(many=True, source='sampled_values')

    class Meta:
        model = MeterValue
        fields = ['timestamp', 'sampledValue']

    def create(self, validated_data):
        sampled_values_data = validated_data.pop('sampled_values')
        meter_value = MeterValue.objects.create(**validated_data)
        
        for sampled_value_data in sampled_values_data:
            SampledValue.objects.create(meter_value=meter_value, **sampled_value_data)

        return meter_value

    def update(self, instance, validated_data):
        sampled_values_data = validated_data.pop('sampled_values')
        
        instance.timestamp = validated_data.get('timestamp', instance.timestamp)
        instance.save()

        instance.sampled_values.all().delete()
        for sampled_value_data in sampled_values_data:
            SampledValue.objects.create(meter_value=instance, **sampled_value_data)

        return instance

class MeterValuesRequestSerializer(ChargerRequestBaseSerializer):
    meterValue = MeterValueSerializer(many=True, source='meter_value')
    connectorId = serializers.IntegerField(source='connector_id')
    transactionId = serializers.IntegerField(source='transaction_id')
    class Meta:
        model = MeterValuesRequest
        fields = ['connectorId', 'transactionId', 'meterValue']

    def create(self, validated_data):
        meter_value_data = validated_data.pop('meter_value')
        meter_values_request = MeterValuesRequest.objects.create(**validated_data)

        for meter_value_data in meter_value_data:
            sampled_values_data = meter_value_data.pop('sampled_values')
            meter_value = MeterValue.objects.create(operation=meter_values_request, **meter_value_data)
            
            for sampled_value_data in sampled_values_data:
                SampledValue.objects.create(meter_value=meter_value, **sampled_value_data)
        
        return meter_values_request

serializer_types_map = {
    'datatransfer': DataTransferRequestSerializer,
    'metervalues': MeterValuesRequestSerializer,
}
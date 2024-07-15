from rest_framework import serializers

from log_processor.models import DataTransfer


class DataTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataTransfer
        fields = ['vendorId', 'messageId', 'data']


serializer_types_map = {
    'datatransfer': DataTransferSerializer
}
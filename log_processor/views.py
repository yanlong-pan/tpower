# Create your views here.
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import TextSerializer
from .serializers import DataTransferSerializer

class SubmitView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = TextSerializer(data=request.data)
        if serializer.is_valid():
            text = serializer.validated_data.get('text')
            return Response({"message": f"Received text: {text}"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class DataTransferAPIView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            serializer = DataTransferSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({'error': str(e), 'input': request.data}, status=status.HTTP_400_BAD_REQUEST)
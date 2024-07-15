import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from utilities import loggers
from .serializers import serializer_types_map

def parse_log_record_input(data):
    patterns = [
        re.compile(r'ocpp:([\w|\d]+):.+receive message\s*\[.+,.+,\s*\"(\w+)\"\s*,\s*(\{.+\})\s*]')
        # Add more patterns here to parse the input string
    ]
    for p in patterns:
        match = p.search(data)
        if match:
            return match.groups()
    # If no match is found for known patterns, then it means that the input format is not supported yet
    loggers.error_file_logger.error(f'Unsupported format: {data}')
    raise ValueError("Unsupported input format")

class DataTransferAPIView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            chargernum, keyword, content = parse_log_record_input(request.data)
            # Choose correct serializer
            serializer = serializer_types_map[keyword.lower()](data=content)
            # Validate and save to DB
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # No serializer is bound to the keyword
        except KeyError as e:
            msg = f'Unknown: {keyword}'
            loggers.error_file_logger.error(msg, exc_info=True)
            return Response({
                'success': False,
                'message': msg
            }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({
                'success': False,
                'message': {
                    'error': str(e),
                }
            }, status=status.HTTP_400_BAD_REQUEST)
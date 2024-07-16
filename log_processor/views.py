import json
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from utilities import loggers
from .serializers import serializer_types_map

def parse_log_record_input(data: str):
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

    def _success_response_body(self, msg):
        return {
            'success': True,
            'message': msg
        }

    def _failed_response_body(self, err_msg):
        return {
            'success': False,
            'message': {
                'error': err_msg
            }
        }

    def post(self, request, *args, **kwargs):
        try:
            # Parse input and format data
            chargernum, keyword, content = parse_log_record_input(request.data)
            content = {'chargerNumber': chargernum, **json.loads(content)}
            try:
                # Choose correct serializer
                keyword_serializer_clazz = serializer_types_map[keyword.lower()]
            # No serializer is bound to the keyword
            except KeyError as e:
                msg = f'Unsupported: {keyword}'
                loggers.error_file_logger.error(msg, exc_info=True)
                return Response(self._failed_response_body(msg), status=status.HTTP_400_BAD_REQUEST)

            serializer = keyword_serializer_clazz(data=content)
            # Validate and save to DB
            if serializer.is_valid():
                serializer.save()
                return Response(self._success_response_body(serializer.data), status=status.HTTP_201_CREATED)
            else:
                return Response(self._failed_response_body(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            loggers.error_file_logger.error('Exception ', exc_info=True)
            return Response(self._failed_response_body(str(e)), status=status.HTTP_400_BAD_REQUEST)
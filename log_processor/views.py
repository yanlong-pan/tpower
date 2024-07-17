import json
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers

from log_processor import errors
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
    raise errors.CurrentlyUnSupported(errors.ErrorMessage.UNSUPPORTED_INPUT_FORMAT.value)

def api_success_response_body(msg):
    return {
        'success': True,
        'message': msg
    }

def api_failed_response_body(err_msg):
    return {
        'success': False,
        'message': {
            'error': err_msg
        }
    }
class ProcessChargerSentLogsAPIView(APIView):

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
                msg = f'{errors.ErrorMessage.UNSUPPORTED_CHARGER_SENT_REQUEST_TYPE.value}: {keyword}'
                loggers.error_file_logger.error(msg, exc_info=True)
                return Response(api_failed_response_body(msg), status=status.HTTP_400_BAD_REQUEST)

            serializer: serializers.ModelSerializer = keyword_serializer_clazz(data=content)
            # Validate and save to DB
            if serializer.is_valid():
                serializer.save()
                return Response(api_success_response_body(serializer.data), status=status.HTTP_201_CREATED)
            else:
                loggers.error_file_logger.error(serializer.errors, exc_info=True)
                return Response(api_failed_response_body(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        except errors.CurrentlyUnSupported as e:
            loggers.error_file_logger.error(e.message, exc_info=True)
            return Response(api_failed_response_body(e.message), status=status.HTTP_406_NOT_ACCEPTABLE)

        except:
            loggers.error_file_logger.error(errors.ErrorMessage.UNHANDLED_EXCEPTION.value, exc_info=True)
            return Response(errors.ErrorMessage.INTERNAL_SERVER_ERROR.value, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
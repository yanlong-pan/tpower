from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from log_processor import errors
from log_processor.parser import ParserOutput, parse_input
from utilities import loggers

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
            all_serialized_data = []
            # Parse input
            output: ParserOutput = parse_input(request.data)
            # Validate and save to DB
            for model_data in output.parsed_models:
                serializer = output.serializer_clz(data=model_data)
                if serializer.is_valid():
                    serializer.save()
                    all_serialized_data.append(serializer.data)
                else:
                    loggers.error_file_logger.error(serializer.errors, exc_info=True)
                    return Response(api_failed_response_body(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
            return Response(api_success_response_body(all_serialized_data), status=status.HTTP_201_CREATED)
        except errors.CurrentlyUnSupported as e:
            loggers.error_file_logger.error(e.message, exc_info=True)
            return Response(api_failed_response_body(e.message), status=status.HTTP_406_NOT_ACCEPTABLE)

        except:
            loggers.error_file_logger.error(errors.ErrorMessage.UNHANDLED_EXCEPTION.value, exc_info=True)
            return Response(api_failed_response_body(errors.ErrorMessage.INTERNAL_SERVER_ERROR.value), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
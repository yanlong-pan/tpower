import json
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from log_processor import errors
from log_processor.views import api_failed_response_body
from utilities import loggers


CORRECT_METERVALUES_LOG_RECORD = """
INFO:ocpp:TH007: receive message [2,"1ycg31azvoem8b8kjxjak1s0","MeterValues",{"connectorId":1,"transactionId":78450704,"meterValue":[{"timestamp":"2024-07-09T07:18:36Z","sampledValue":[{"value":"64059","context":"Sample.Periodic","measurand":"Energy.Active.Import.Register","format":"Raw","unit":"Wh"},{"value":"5543","measurand":"Power.Active.Import","format":"Raw","unit":"W"}]}]}]
"""
METERVALUES_LOG_RECORD_WITH_UNSUPPORTED_REGEX_PATTERN="""
INFO:ocpp:TH007: send [2,"1ycg31azvoem8b8kjxjak1s0","MeterValues",{"connectorId":1,"transactionId":78450704,"meterValue":[{"timestamp":"2024-07-09T07:18:36Z","sampledValue":[{"value":"64059","context":"Sample.Periodic","measurand":"Energy.Active.Import.Register","format":"Raw","unit":"Wh"}]}]}]
""" # "send" should be "receive message"
METERVALUES_LOG_RECORD_WITH_UNSUPPORTED_SAMPLEDVALUE = """
INFO:ocpp:TH007: receive message [2,"1ycg31azvoem8b8kjxjak1s0","MeterValues",{"connectorId":1,"transactionId":78450704,"meterValue":[{"timestamp":"2024-07-09T07:18:36Z","sampledValue":[{"value":"64059","context":"Sample.Periodics","measurand":"Energy.Active.Import.Register","format":"Raw","unit":"Wh"},{"value":"5543","measurand":"Power.Active.Import","format":"Raw","unit":"W"}]}]}]
""" # "context":"Sample.Periodics" should be "Sample.Periodic"
CORRECT_DATATRANSFER_LOG_RECORD = """
INFO:ocpp:1000191: receive message [2,"104","DataTransfer",{"vendorId":"ATESS","messageId":"currentrecord","data":"id=0&connectorId=0&chargemode=0&starttime=2000-00-00 00:00:00&endtime=2000-00-00 00:00:00&costenergy=0&costmoney=0&transactionId=0&workmode=0"}]
"""
DATATRANSFER_LOG_RECORD_WITH_WRONG_FORMAT = """
INFO:ocpp:1000191: receive message [2,"104","DataTransfer",{"vendorId":"ATESS","messageId":"currentrecord","data":{"id": "0", "connectorId": "0", "chargemode": "0", "starttime": "2000-00-00 00:00:00", "endtime": "2000-00-00 00:00:00", "costenergy": "0", "costmoney": "0", "transactionId": "0", "workmode": "0"}}]
""" # data should be a string instead of a dict
LOG_RECORD_WITH_UNSUPPORTED_KEYWORD = """
INFO:ocpp:1000186: receive message [ 2, "1000186-14", "Authorize", { "idTag" : "5d2e7089" } ]
""" # "Authorize" is a valid keyword according to the OCPP standrd but is not yet supported in current stage of the project

class ProcessChargerSentLogsAPIViewTests(TestCase):

    def _process_charger_sent_logs(self, record_str):
        return self.client.post(
            path=reverse('log_processor:process-charger-sent-logs'),
            data=json.dumps(record_str),
            content_type='application/json',
        )

    def setUp(self) -> None:
        # Mute loggers in app
        loggers.mute_logger(loggers.debug_file_logger)
        loggers.mute_logger(loggers.error_file_logger)

    def tearDown(self) -> None:
        # Unmute loggers in app
        loggers.unmute_logger(loggers.debug_file_logger)
        loggers.unmute_logger(loggers.error_file_logger)

    def test_process_correct_metervalues_log_record(self):
        response = self._process_charger_sent_logs(CORRECT_METERVALUES_LOG_RECORD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) 

    def test_process_metervalues_log_record_with_wrong_format(self):
        response = self._process_charger_sent_logs(METERVALUES_LOG_RECORD_WITH_UNSUPPORTED_REGEX_PATTERN)
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            api_failed_response_body(errors.ErrorMessage.UNSUPPORTED_INPUT_FORMAT.value)
        )

    def test_process_metervalues_log_record_with_unsupported_sampledvalue(self):
        response = self._process_charger_sent_logs(METERVALUES_LOG_RECORD_WITH_UNSUPPORTED_SAMPLEDVALUE)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            api_failed_response_body({
                "meterValue": [
                    {
                        "sampledValue": [
                            {
                                "context": [
                                    '"Sample.Periodics\" is not a valid choice.'
                                ]
                            },
                            {}
                        ]
                    }
                ]
            })
        )

    def test_process_correct_datatransfer_log_record(self):
        response = self._process_charger_sent_logs(CORRECT_DATATRANSFER_LOG_RECORD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) 

    def test_process_datatransfer_log_record_with_wrong_format(self):
        response = self._process_charger_sent_logs(DATATRANSFER_LOG_RECORD_WITH_WRONG_FORMAT)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            api_failed_response_body({
                "data": [
                    "Not a valid string."
                ]
            })
        )

    def test_process_log_record_with_unsupported_keyword(self):
        response = self._process_charger_sent_logs(LOG_RECORD_WITH_UNSUPPORTED_KEYWORD)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            api_failed_response_body(f'{errors.ErrorMessage.UNSUPPORTED_CHARGER_SENT_REQUEST_TYPE.value}: Authorize')
        )

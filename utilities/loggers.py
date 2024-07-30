import logging
from kuai_log import get_logger
from kuai_log.logger import KuaiLogger

debug_file_logger = get_logger(name='debug_file_logger', level=logging.DEBUG, log_filename='debug.log',
                log_path='statics/logs/app/debug', is_add_file_handler=True,
                json_log_path='statics/logs/app/debug/json', is_add_json_file_handler=True,
            )

error_file_logger = get_logger(name='error_file_logger', level=logging.ERROR, log_filename='error.log',
                log_path='statics/logs/app/error', is_add_file_handler=True,
                json_log_path='statics/logs/app/error/json', is_add_json_file_handler=True,
            )

test_logger = get_logger(name='test_logger', level=logging.ERROR)

def mute_logger(logger: KuaiLogger):
    logger._is_add_stream_handler = False
    logger._is_add_file_handler = False
    logger._is_add_json_file_handler = False

def unmute_logger(logger: KuaiLogger):
    logger._is_add_stream_handler = True
    logger._is_add_file_handler = True
    logger._is_add_json_file_handler = True
from enum import Enum

class ErrorMessage(Enum):
    UNSUPPORTED_INPUT_FORMAT = "Unsupported input format"
    UNSUPPORTED_CHARGER_SENT_REQUEST_TYPE = "Unsupported charger sent request type"
    UNHANDLED_EXCEPTION = "Unhandled exception"
    INTERNAL_SERVER_ERROR = "Internal server error"
    NOT_CONFIGURED = "Not configured"

class CurrentlyUnSupported(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
import decimal
from django.core.exceptions import ValidationError


def decimal_or_signed_data(value):
    # Attempt to convert the value to a decimal number
    try:
        decimal.Decimal(value)
    except decimal.InvalidOperation:
        # If it cannot be converted to a decimal number, check if it is encoded as hex data
        if not isinstance(value, str):
            raise ValidationError('Value must be either a decimal number or a signed string.')
        else:
            int(value, 16)
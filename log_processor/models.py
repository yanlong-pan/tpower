from datetime import datetime
from enum import Enum
from typing import Optional, Sequence
from django.db import models

from django.db import models
from pydantic import BaseModel
from django_pydantic_field import SchemaField

class ReadingContext(str, Enum):
    INTERRUPTION_BEGIN = 'Interruption.Begin' # Value taken at start of interruption'
    INTERRUPTION_END = 'Interruption.End' # Value taken when resuming after interruption'
    OTHER = 'Other' # Value for any other situations'
    SAMPLE_CLOCK = 'Sample.Clock' # Value taken at clock aligned interval'
    SAMPLE_PERIODIC = 'Sample.Periodic' # Value taken as periodic sample relative to start time of transaction'
    TRANSACTION_BEGIN = 'Transaction.Begin' # Value taken at start of transaction'
    TRANSACTION_END = 'Transaction.End' # Value taken at end of transaction'
    TRIGGER = 'Trigger' # Value taken in response to a TriggerMessage.req'

class ValueFormat(str, Enum):
    RAW = 'Raw' # Data is to be interpreted as integer/decimal numeric data.'
    SIGNEDDATA = 'SignedData' # Data is represented as a signed binary data block, encoded as hex data'

class Measurand(str, Enum):
    CURRENT_EXPORT = 'Current.Export' # Instantaneous current flow from EV'
    CURRENT_IMPORT = 'Current.Import' # Instantaneous current flow to EV'
    CURRENT_OFFERED = 'Current.Offered' # Maximum current offered to EV'
    ENERGY_ACTIVE_EXPORT_REGISTER = 'Energy.Active.Export.Register' # Numerical value read from the "active electrical energy" (Wh or kWh) register of the (most authoritative) electrical meter measuring energy exported (to the grid).
    ENERGY_ACTIVE_IMPORT_REGISTER = 'Energy.Active.Import.Register' # Numerical value read from the "active electrical energy" (Wh or kWh) register of the (most authoritative) electrical meter measuring energy imported (from the grid supply).
    ENERGY_REACTIVE_EXPORT_REGISTER = 'Energy.Reactive.Export.Register' # Numerical value read from the "reactive electrical energy" (VARh or kVARh) register of the (most authoritative) electrical meter measuring energy exported (to the grid).
    ENERGY_REACTIVE_IMPORT_REGISTER = 'Energy.Reactive.Import.Register' # Numerical value read from the "reactive electrical energy" (VARh or kVARh) register of the (most authoritative) electrical meter measuring energy imported (from the grid supply).
    ENERGY_ACTIVE_EXPORT_INTERVAL = 'Energy.Active.Export.Interval' # Absolute amount of "active electrical energy" (Wh or kWh) exported (to the grid) during an associated time "interval", specified by a Metervalues ReadingContext, and applicable interval duration configuration values (in seconds) for "ClockAlignedDataInterval" and "MeterValueSampleInterval".
    ENERGY_ACTIVE_IMPORT_INTERVAL = 'Energy.Active.Import.Interval' # Absolute amount of "active electrical energy" (Wh or kWh) imported (from the grid supply) during an associated time "interval", specified by a Metervalues ReadingContext, and applicable interval duration configuration values (in seconds) for "ClockAlignedDataInterval" and "MeterValueSampleInterval".
    ENERGY_REACTIVE_EXPORT_INTERVAL = 'Energy.Reactive.Export.Interval' # Absolute amount of "reactive electrical energy" (VARh or kVARh) exported (to the grid) during an associated time "interval", specified by a Metervalues ReadingContext, and applicable interval duration configuration values (in seconds) for "ClockAlignedDatalnterval" and "MeterValueSampleInterval".
    ENERGY_REACTIVE_IMPORT_INTERVAL = 'Energy.Reactive.Import.Interval' # Absolute amount of "reactive electrical energy" (VARh or kVARh) imported (from the grid supply) during an associated time "interval", specified by a Metervalues ReadingContext, and applicable interval duration configuration values (in seconds) for "ClockAlignedDataInterval" and "MeterValueSampleInterval".
    FREQUENCY = 'Frequency' # Instantaneous reading of powerline frequency. NOTE: OCPP 1.6 does not have a UnitOfMeasure for frequency, the UnitOfMeasure for any SampledValue with measurand: Frequency is Hertz.
    POWER_ACTIVE_EXPORT = 'Power.Active.Export' # Instantaneous active power exported by EV. (W or kW)
    POWER_ACTIVE_IMPORT = 'Power.Active.Import' # Instantaneous active power imported by EV. (W or kW)
    POWER_FACTOR = 'Power.Factor' # Instantaneous power factor of total energy flow
    POWER_OFFERED = 'Power.Offered' # Maximum power offered to EV
    POWER_REACTIVE_EXPORT = 'Power.Reactive.Export' # Instantaneous reactive power exported by EV. (var or kvar)
    POWER_REACTIVE_IMPORT = 'Power.Reactive.Import' # Instantaneous reactive power imported by EV. (var or kvar)
    RPM = 'RPM' # Fan speed in RPM
    SOC = 'SoC' # State of charge of charging vehicle in percentage
    TEMPERATURE = 'Temperature' # Temperature reading inside Charge Point.
    VOLTAGE = 'Voltage' # Instantaneous AC RMS supply voltage

class Phase(str, Enum):
    L1 = 'L1' # Measured on L1
    L2 = 'L2' # Measured on L2
    L3 = 'L3' # Measured on L3
    N = 'N' # Measured on Neutral
    L1_N = 'L1-N' # Measured on L1 with respect to Neutral conductor
    L2_N = 'L2-N' # Measured on L2 with respect to Neutral conductor
    L3_N = 'L3-N' # Measured on L3 with respect to Neutral conductor
    L1_L2 = 'L1-L2' # Measured between L1 and L2
    L2_L3 = 'L2-L3' # Measured between L2 and L3
    L3_L1 = 'L3-L1' # Measured between L3 and L1

class Location(str, Enum):
    BODY = 'Body' # Measurement inside body of Charge Point (e.g. Temperature)
    CABLE = 'Cable' # Measurement taken from cable between EV and Charge Point
    EV = 'EV' # Measurement taken by EV
    INLET = 'Inlet' # Measurement at network (“grid”) inlet connection
    OUTLET = 'Outlet' # Measurement at a Connector. Default value

class UnitOfMeasure(str, Enum):
    WH = 'Wh' # Watt-hours (energy). Default.
    KWH = 'kWh' # kiloWatt-hours (energy).
    VARH = 'varh' # Var-hours (reactive energy).
    KVARH = 'kvarh' # kilovar-hours (reactive energy).
    W = 'W' # Watts (power).
    KW = 'kW' # kilowatts (power).
    VA = 'VA' # VoltAmpere (apparent power).
    KVA = 'kVA' # kiloVolt Ampere (apparent power).
    VAR = 'var' # Vars (reactive power).
    KVAR = 'kvar' # kilovars (reactive power).
    A = 'A' # Amperes (current).
    V = 'V' # Voltage (r.m.s. AC).
    CELSIUS = 'Celsius' # Degrees (temperature).
    FAHRENHEIT = 'Fahrenheit' # Degrees (temperature).
    K = 'K' # Degrees Kelvin (temperature).
    PERCENT = 'Percent' # Percentage.

class SampledValue(BaseModel):
    timestamp: datetime
    value: str
    context: Optional[ReadingContext] = ReadingContext.SAMPLE_PERIODIC
    format: Optional[ValueFormat] = ValueFormat.RAW
    measurand: Optional[Measurand] = Measurand.ENERGY_ACTIVE_EXPORT_REGISTER
    phase: Optional[Phase] = None
    location: Optional[Location] = Location.OUTLET
    unit: Optional[UnitOfMeasure] = UnitOfMeasure.WH

# ORMs
class ChargerSentRequestMixin(models.Model):
    charger_number = models.CharField(max_length=64)
    class Meta:
        abstract = True

class DataTransferRequest(ChargerSentRequestMixin, models.Model):
    vendor_id = models.CharField(max_length=255)
    message_id = models.CharField(max_length=50, blank=True)
    data = models.TextField(blank=True)
    raw_data = models.TextField()

class SampledMeterValue(ChargerSentRequestMixin, models.Model):
    connector_id = models.IntegerField()
    transaction_id = models.IntegerField()

    L1: Sequence[SampledValue] = SchemaField()
    L2: Sequence[SampledValue] = SchemaField()
    L3: Sequence[SampledValue] = SchemaField()

    raw_data = models.TextField()
    



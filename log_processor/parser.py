import json
import re
from typing import Callable, Dict, List, Type
from pydantic import BaseModel
from rest_framework import serializers

from log_processor import errors, models
from log_processor.errors import ErrorMessage
from scripts import patterns
from utilities import comparator
from .serializers import SERIALIZER_TYPES_MAP
from django.core.exceptions import ValidationError

class ParserOutput(BaseModel):
    parsed_models: List[Dict]
    serializer_clz: Type[serializers.ModelSerializer]

class ParserStepIO(BaseModel, extra='allow'):
    content: List[Dict]
    request_type: str

class BaseParser(BaseModel):
    steps: List[Callable[[ParserStepIO], ParserStepIO]]

    def _parse(self, input: ParserStepIO) -> ParserStepIO:
        result = input
        for step in self.steps:
            result = step(result)
        return result

    def parsed(self, input: ParserStepIO) -> ParserOutput:
        r = self._parse(input)
        try:
            serializer_clz = SERIALIZER_TYPES_MAP[r.request_type]
        except KeyError:
            raise errors.CurrentlyUnSupported(ErrorMessage.UNSUPPORTED_CHARGER_SENT_REQUEST_TYPE.value)
        return ParserOutput(parsed_models=r.content, serializer_clz=serializer_clz)

def add_charger_number_and_raw_data_to_content(data: ParserStepIO) -> ParserStepIO:
    data_dict = data.model_dump()

    # Update content field
    data_dict['content'] = [{
        'charger_number': data.charger_number,
        **json.loads(data.content[0]['json_str']),
        'raw_data': data.raw_data,
    }]

    return ParserStepIO(**data_dict)

def flatten_meter_value(data: ParserStepIO) -> ParserStepIO:
    # Extract basic information
    prev_content = data.content[0]
    meter_values = prev_content["meterValue"]
    prev_content.pop("meterValue", None)
    # Collect all sampled values and add missing fields
    all_sampled_values = []
    for meter_value in meter_values:
        timestamp = meter_value["timestamp"]
        for sampled_value in meter_value["sampledValue"]:
            if sampled_value.get('measurand') == 'Voltage' and not sampled_value.get('unit'):
                sampled_value['unit'] = 'V'
            all_sampled_values.append({
                "timestamp": timestamp,
                **sampled_value
            })

    r = ParserStepIO(content=[{
        "all_sampled_values": all_sampled_values,
        **prev_content
    }], request_type=data.request_type)
    
    return r

def process_sampled_values(data: ParserStepIO) -> ParserStepIO:
    def _same_type_sample_values(to_compare: dict, values: List[dict], ignores: List[str] = ["value", "phase", "timestamp"]) -> List[dict]:
        return [v for v in values if comparator.shallow_compare_two_dicts(v, to_compare, ignores)]

    # Extract basic information
    prev_content = data.content[0]
    all_sampled_values = prev_content["all_sampled_values"]

    # Define phases and units
    valid_units = {'V', 'Wh', 'W', 'A'}
    l_phases = {"L1", "L2", "L3"}
    all_phases = l_phases.union({None, "L1-N", "L2-N", "L3-N", "L1-L2", "L2-L3", "L3-L1"})

    # Initialize result dictionary
    merged_result = {
        "charger_number": prev_content['charger_number'],
        "connector_id": prev_content["connectorId"],
        "transaction_id": prev_content["transactionId"],
        "raw_data": prev_content['raw_data'],
    }
    for phase in l_phases:
        merged_result[phase] = {unit: [] for unit in valid_units}

    # Initialize dictionaries to store phases for each unit
    phases_dict = {unit: set() for unit in valid_units}

    # Populate phases to process for each valid unit
    for sampled_value in all_sampled_values:
        unit = sampled_value.get("unit")
        if unit in valid_units:
            phase = sampled_value.get("phase")
            if phase in all_phases:
                phases_dict[unit].add(phase)

    # Initialize a dictionary to store values for each phase
    phase_unit_sampled_values = {phase: {unit: [] for unit in valid_units} for phase in l_phases}
        
    # Categorize sampledValues
    for sampled_value in all_sampled_values:
        value = float(sampled_value["value"])
        phase = sampled_value.get("phase")
        unit = sampled_value.get("unit")

        if unit in valid_units and phase in phases_dict[unit] and value > 0:
            # When phase is absent, the measured value is interpreted as an overall value. Default to L1
            phase_unit_sampled_values[phase[:2] if phase else "L1"][unit].append(sampled_value)

    # Process L1 sampled values
    for unit, d in phase_unit_sampled_values["L1"].items():
        for stored_sampled_value in d:
            # If there is an overall item
            if not stored_sampled_value.get("phase"):
                # L1 retains the overall item
                merged_result["L1"][unit].append(stored_sampled_value)
            # If it is not an overall item and there is no same type item, check whether it is single-phase or three-phase
            elif len(_same_type_sample_values(stored_sampled_value, merged_result["L1"][unit])) == 0:
                # If both of the next two phases have values, it is three-phase
                l2_same_type_sample_values = _same_type_sample_values(stored_sampled_value, phase_unit_sampled_values["L2"][unit])
                l3_same_type_sample_values = _same_type_sample_values(stored_sampled_value, phase_unit_sampled_values["L3"][unit])
                if len(l2_same_type_sample_values) > 0 and len(l3_same_type_sample_values) > 0:
                    merged_result["L1"][unit].append(stored_sampled_value)
                    merged_result["L2"][unit].extend(l2_same_type_sample_values)
                    merged_result["L3"][unit].extend(l3_same_type_sample_values)
                # If both of the next two phases are empty, it is single-phase
                elif len(l2_same_type_sample_values) == 0 and len(l3_same_type_sample_values) == 0:
                    merged_result["L1"][unit].append(stored_sampled_value)
                else:
                    raise ValidationError(f"Invalid data format: {stored_sampled_value} should either be a single-phase or triphase")

    # Process L2 & L3 sampled values
    supplements = {unit: [] for unit in valid_units}
    for phase in ["L2", "L3"]:
        for unit, d in phase_unit_sampled_values[phase].items():
            # If it is not in L1, add it to L1
            for stored_sampled_value in d:
                if not _same_type_sample_values(stored_sampled_value, merged_result["L1"][unit]):
                    is_having_same_type = _same_type_sample_values(stored_sampled_value, supplements[unit])
                    supplements[unit].append(stored_sampled_value)
                    if is_having_same_type:
                        # Both L2 & L3 have the same type while L1 doesn't
                        raise ValidationError(f"Invalid phase configuration! Should either be single-phase or triphase, now {supplements[unit]}")
    for u, s in supplements.items():
        merged_result["L1"][u].extend(s)

    # Merge the phase values into the result
    for phase in l_phases:
        merged_result[phase] = [i for lst in merged_result[phase].values() for i in lst]

    r = ParserStepIO(content=[merged_result], request_type=data.request_type)
    return r

CHARGER_REQUEST_PARSER_MAP = {
    'datatransfer': BaseParser(steps=[add_charger_number_and_raw_data_to_content]),
    'metervalues': BaseParser(steps=[add_charger_number_and_raw_data_to_content, flatten_meter_value, process_sampled_values]),
}

class ParserPattern(BaseModel):
    pattern: re.Pattern
    build_parser_input: Callable[[tuple], ParserStepIO]

def parse_input(data: str) -> ParserOutput:
    parser_patterns: List[ParserPattern] = [
        ParserPattern(
            pattern=re.compile(r'ocpp:([\w|\d]+):.+receive message\s*\[.+,.+,\s*\"(\w+)\"\s*,\s*(\{.+\})\s*]'),
            build_parser_input=lambda x,y,z: ParserStepIO(**{
                'charger_number': x,
                'request_type': y.lower(),
                'content': [{'json_str': z}],
                'raw_data': data
            })
        ),
        ParserPattern(
            pattern=re.compile(patterns.CONSUMERS_REGEX.pattern + r'\[(\w+)\].+?\[.+,.+,\s*\"(\w+)\"\s*,\s*(\{.+\})\s*]'),
            build_parser_input=lambda x,y,z: ParserStepIO(**{
                'charger_number': x,
                'request_type': y.lower(),
                'content': [{'json_str': z}],
                'raw_data': data
            })
        ),

        # Add more patterns here to parse the input string
    ]
    for pp in parser_patterns:
        match = pp.pattern.search(data)
        if match:
            r = pp.build_parser_input(*match.groups())
            try:
                parser: BaseParser = CHARGER_REQUEST_PARSER_MAP[r.request_type]
            except KeyError:
                raise errors.CurrentlyUnSupported(ErrorMessage.NOT_CONFIGURED.value + f': {match.group(2)}')
            return parser.parsed(r)
    # If no match is found for known patterns, then it means that the input format is not supported yet
    raise errors.CurrentlyUnSupported(ErrorMessage.UNSUPPORTED_INPUT_FORMAT.value)
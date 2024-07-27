import json
import re
from typing import Callable, Dict, List, Type
from pydantic import BaseModel
from rest_framework import serializers

from log_processor import errors, models
from log_processor.errors import ErrorMessage
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
    def _diff_type_sample_values(to_compare: dict, values: List[dict], ignores: List[str] = ["value", "phase"]) -> List[dict]:
        return [v for v in values if not comparator.shallow_compare_two_dicts(v, to_compare, ignores)]
    def _same_type_sample_values(to_compare: dict, values: List[dict], ignores: List[str] = ["value", "phase"]) -> List[dict]:
        return [v for v in values if comparator.shallow_compare_two_dicts(v, to_compare, ignores)]

    # Extract basic information
    content = data.content[0]
    connector_id = content["connectorId"]
    transaction_id = content["transactionId"]
    meter_values = content["meterValue"]

    valid_units = {'V', 'Wh', 'W', 'A'}
    l_phases = {"L1", "L2", "L3"}
    l_n_phases = {"L1-N", "L2-N", "L3-N"}
    l_l_phases = {"L1-L2", "L2-L3", "L3-L1"}
    all_phases = l_phases.union(l_n_phases).union(l_l_phases)
    valid_phases = {
        frozenset(l_phases),
        frozenset(l_n_phases),
        frozenset(l_l_phases),
        frozenset(l_phases.union(l_n_phases)),
        frozenset(l_phases.union(l_l_phases)),
        frozenset(l_n_phases.union(l_l_phases)),
        frozenset(all_phases),
    }

    # Initialize result dictionary
    merged_result = {
        "charger_number": content['charger_number'],
        "connector_id": connector_id,
        "transaction_id": transaction_id,
        "raw_data": content['raw_data'],
        "L1": {unit: [] for unit in valid_units},
        "L2": {unit: [] for unit in valid_units},
        "L3": {unit: [] for unit in valid_units},
    }
    # for phase in l_phases:
    #     merged_result[phase] = {phase: {unit: []} for phase in l_phases for unit in valid_units}

    # Iterate through each meterValue
    for meter_value in meter_values:
        timestamp = meter_value["timestamp"]

        # Check phase conditions
        phases = {sampled_value.get("phase") for sampled_value in meter_value["sampledValue"] if sampled_value.get("phase") in all_phases}

        # Determine the target phases based on the present phases in the data
        if not phases:
            target_phases = {None}
        elif frozenset(phases) in valid_phases:
            target_phases = phases
        else:
            raise ValidationError("Invalid phase configuration in sampled values")

        # Initialize a dictionary to store values for each phase
        phase_values = phase_values = {phase: {unit: [] for unit in valid_units} for phase in l_phases}
        
        # Iterate through each sampledValue
        for sampled_value in meter_value["sampledValue"]:
            value = float(sampled_value["value"])
            phase = sampled_value.get("phase")
            unit = sampled_value.get("unit", models.UnitOfMeasure.WH.value)
            context = sampled_value.get("context", models.ReadingContext.SAMPLE_PERIODIC.value)
            format = sampled_value.get("format", models.ValueFormat.RAW.value)
            measurand = sampled_value.get("measurand", models.Measurand.ENERGY_ACTIVE_EXPORT_REGISTER.value)
            location = sampled_value.get("location", models.Location.OUTLET.value)
            location = sampled_value.get("location", models.Location.OUTLET.value)
            sampled_value_with_timestamp = {
                "timestamp": timestamp,
                "value": value,
                "context": context,
                "format": format,
                "measurand": measurand,
                "phase": phase,
                "location": location,
                "unit": unit,
            }

            if unit in valid_units and phase in target_phases and value > 0:
                # When phase is absent, the measured value is interpreted as an overall value. 默认放入L1
                phase_values[phase[:2] if phase else "L1"][unit].append(sampled_value_with_timestamp)

        for unit, d in phase_values["L1"].items():
            for phase_value in d:
                # 如果存在 overall 项
                if not phase_value.get("phase"):
                    # L1保留 overall项
                    merged_result["L1"][unit].append(phase_value)
                # 如果不是 overall 项，且未保过 存同类项，则需要检查是单相还是三相
                elif len(_same_type_sample_values(phase_value, merged_result["L1"][unit])) == 0:
                        # 如果后两相都存在值，则为三相
                        l2_same_type_sample_values = _same_type_sample_values(phase_value, phase_values["L2"][unit])
                        l3_same_type_sample_values = _same_type_sample_values(phase_value, phase_values["L3"][unit])
                        if len(l2_same_type_sample_values) > 0 and len(l3_same_type_sample_values) > 0:
                            merged_result["L1"][unit].append(phase_value)
                            merged_result["L2"][unit].extend(l2_same_type_sample_values)
                            merged_result["L3"][unit].extend(l3_same_type_sample_values)
                        # 如果后两相都为空, 则为单相
                        elif len(l2_same_type_sample_values) == 0 and len(l3_same_type_sample_values) == 0:
                            merged_result["L1"][unit].append(phase_value)
                        else:
                            raise ValidationError(f"Invalid data format: {phase_value["measurand"]} should either be a single-phase or triphase")

        for phase in ["L2", "L3"]:
            for unit, d in phase_values[phase].items():
                # 如果L1中没有，则加到L1
                for phase_value in d:
                    if not _same_type_sample_values(phase_value, merged_result["L1"][unit]):
                        merged_result["L1"][unit].append(phase_value)

        # Merge the phase values into the result
        for phase in l_phases:
            merged_result[phase] = [i for lst in merged_result[phase].values() for i in lst]

    r = ParserStepIO(content=[merged_result], request_type=data.request_type)
    return r

CHARGER_REQUEST_PARSER_MAP = {
    'datatransfer': BaseParser(steps=[add_charger_number_and_raw_data_to_content]),
    'metervalues': BaseParser(steps=[add_charger_number_and_raw_data_to_content, flatten_meter_value]),
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
        )
        
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
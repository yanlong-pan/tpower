import json
import re
from typing import Callable, Dict, List, Type
from pydantic import BaseModel
from rest_framework import serializers

from log_processor import errors
from log_processor.errors import ErrorMessage
from .serializers import SERIALIZER_TYPES_MAP


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
    content = data.content[0]
    connector_id = content["connectorId"]
    transaction_id = content["transactionId"]
    meter_values = content["meterValue"]

    # Initialize result dictionary
    merged_result = {
        "charger_number": content['charger_number'],
        "connector_id": connector_id,
        "transaction_id": transaction_id,
        "raw_data": content['raw_data'],
        "L1": [],
        "L2": [],
        "L3": []
    }

    # Iterate through each meterValue
    for meter_value in meter_values:
        timestamp = meter_value["timestamp"]

        # Check phase conditions
        phases = {sampled_value.get("phase") for sampled_value in meter_value["sampledValue"]}
        all_phases = {"L1", "L2", "L3"}
        l_n_phases = {"L1-N", "L2-N", "L3-N"}
        l_l_phases = {"L1-L2", "L2-L3", "L3-L1"}

        # Determine the target phases based on the present phases in the data
        if phases.isdisjoint(all_phases.union(l_n_phases).union(l_l_phases)):
            target_phases = {None}
        elif phases.issubset(all_phases) or phases.issubset(l_n_phases) or phases.issubset(l_l_phases):
            target_phases = phases
        elif phases.intersection(all_phases) or phases.intersection(l_n_phases):
            target_phases = all_phases.union(l_n_phases)
        else:
            raise Exception("Invalid phase configuration in sampled values")

        # Initialize a dictionary to store values for each phase
        phase_values = {"L1": [], "L2": [], "L3": []}

        # Iterate through each sampledValue
        for sampled_value in meter_value["sampledValue"]:
            phase = sampled_value.get("phase")
            if sampled_value["unit"] in {'V', 'Wh', 'W', 'A'}:
                sampled_value_with_timestamp = {**sampled_value, "timestamp": timestamp}
                if phase in target_phases or (target_phases == {None} and phase is None):
                    if phase in {"L1", "L1-N", None}:
                        phase_values["L1"].append(sampled_value_with_timestamp)
                    elif phase in {"L2", "L2-N"}:
                        phase_values["L2"].append(sampled_value_with_timestamp)
                    elif phase in {"L3", "L3-N"}:
                        phase_values["L3"].append(sampled_value_with_timestamp)

        # Merge the phase values into the result
        merged_result["L1"].extend(phase_values["L1"])
        merged_result["L2"].extend(phase_values["L2"])
        merged_result["L3"].extend(phase_values["L3"])

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
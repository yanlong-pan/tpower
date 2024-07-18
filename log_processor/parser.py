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
    # 将数据转换为字典
    data_dict = data.model_dump()

    # 更新 content 字段
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
    
    # Initialize result list
    flattened_list = []
    
    # Iterate through each meterValue
    for meter_value in meter_values:
        timestamp = meter_value["timestamp"]
        
        # Iterate through each sampledValue
        for sampled_value in meter_value["sampledValue"]:
            # Combine information into a dictionary
            flattened_sample = {
                "charger_number": content['charger_number'],
                "timestamp": timestamp,
                "connector_id": connector_id,
                "transaction_id": transaction_id,
                **sampled_value,
                "raw_data": content['raw_data']
            }
            # Add to result list
            flattened_list.append(flattened_sample)
    r = ParserStepIO(content=flattened_list, request_type=data.request_type)
    return r

CHARGER_REQUEST_PARSER_MAP = {
    'datatransfer': BaseParser(steps=[add_charger_number_and_raw_data_to_content]),
    'metervalues': BaseParser(steps=[add_charger_number_and_raw_data_to_content, flatten_meter_value]),
}


def parse_input(data: str) -> ParserOutput:
    patterns = [
        re.compile(r'ocpp:([\w|\d]+):.+receive message\s*\[.+,.+,\s*\"(\w+)\"\s*,\s*(\{.+\})\s*]')
        # Add more patterns here to parse the input string
    ]
    for p in patterns:
        match = p.search(data)
        if match:
            r = ParserStepIO(**{
                'charger_number': match.group(1),
                'request_type': match.group(2).lower(),
                'content': [{'json_str': match.group(3)}],
                'raw_data': data
            })
            try:
                parser: BaseParser = CHARGER_REQUEST_PARSER_MAP[r.request_type]
            except KeyError:
                raise errors.CurrentlyUnSupported(ErrorMessage.NOT_CONFIGURED.value)
            return parser.parsed(r)
    # If no match is found for known patterns, then it means that the input format is not supported yet
    raise errors.CurrentlyUnSupported(ErrorMessage.UNSUPPORTED_INPUT_FORMAT.value)
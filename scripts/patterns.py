from enum import Enum
import json
import re

from pydantic import BaseModel
from typing import Callable
from utilities import comparator

# Regex
THIRD_ARRAY_ITEM_REGEX = re.compile(r'\[\s*\d+\s*,\s*"[^"]+"\s*,\s*"([^"]+)"')
RECEIVE_MESSAGE_REGEX = re.compile(r'receive message.*')
CONSUMERS_REGEX = re.compile(r'consumers.*')
JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM=re.compile(r'\[.+,.+,\s*\"\w+\"\s*,\s*(\{.+\})\s*]')
OCPP_CHARGER_NUM=re.compile(r'ocpp:([\w|\d]+):')

# Identifiers to determine whether a record qualifies for further processing
class ChargerSentMessageIdentifier(str, Enum):
    RECEIVE_MESSAGE = 'receive message'
    CONSUMERS = 'consumers'

# Keyword extraction patterns based on identifiers in raw data
KEYWORD_PATTERNS = {
    ChargerSentMessageIdentifier.RECEIVE_MESSAGE: [re.compile(RECEIVE_MESSAGE_REGEX.pattern + THIRD_ARRAY_ITEM_REGEX.pattern)],
    ChargerSentMessageIdentifier.CONSUMERS: [re.compile(CONSUMERS_REGEX.pattern + THIRD_ARRAY_ITEM_REGEX.pattern)],
}

# Used to compare the structures of extracted contents
class ComparablePattern(BaseModel):
    identifier: str
    pattern: re.Pattern # pattern to extract the contents
    is_identical: Callable[[str, str], bool]

comparable_pattern001 = ComparablePattern(
    identifier=ChargerSentMessageIdentifier.RECEIVE_MESSAGE,
    pattern=re.compile(RECEIVE_MESSAGE_REGEX.pattern + JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM.pattern), # Used to extract content
    is_identical=comparator.compare_json_str # Used to compare if two extacted contents have identical data structures
)

comparable_pattern002 = ComparablePattern(
    identifier=ChargerSentMessageIdentifier.CONSUMERS,
    pattern=re.compile(CONSUMERS_REGEX.pattern + JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM.pattern),
    is_identical=comparator.compare_json_str
)

# A config map to link keyword and its content patterns
COMPARABLE_KEYWORD_CONTENT_MAP = {
    'authorize': [comparable_pattern001, comparable_pattern002],
    'bootnotification': [comparable_pattern001, comparable_pattern002],
    'datatransfer': [
        ComparablePattern(
            identifier=ChargerSentMessageIdentifier.RECEIVE_MESSAGE,
            pattern=re.compile(RECEIVE_MESSAGE_REGEX.pattern + JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM.pattern),
            is_identical = comparator.datatransfer_content_comparator
        ),
        ComparablePattern(
            identifier=ChargerSentMessageIdentifier.CONSUMERS,
            pattern=re.compile(CONSUMERS_REGEX.pattern + JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM.pattern),
            is_identical = comparator.datatransfer_content_comparator
        )
    ],
    'heartbeat': [comparable_pattern001, comparable_pattern002],
    'metervalues': [comparable_pattern001, comparable_pattern002],
    'starttransaction': [comparable_pattern001, comparable_pattern002],
    'statusnotification': [comparable_pattern001, comparable_pattern002],
    'stoptransaction': [comparable_pattern001, comparable_pattern002],
}
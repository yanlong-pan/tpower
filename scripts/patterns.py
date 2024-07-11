import json
import re

from pydantic import BaseModel
from typing import Callable
from utilities import comparator

# Define regex patterns, each should contain a target group
THIRD_ARRAY_ITEM=re.compile(r'receive message \[\s*\d+\s*,\s*"[^"]+"\s*,(.+)\]')
THIRD_ARRAY_ITEM_IN_QUOTES=re.compile(r'receive message \[\s*\d+\s*,\s*"[^"]+"\s*,\s*"([^"]+)"')
JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM=re.compile(r'receive message\s*\[.+,.+,\"\w+\",(\{.+\})[,|\]]')

# Sniffer to identify keywords in raw data
keywords = [THIRD_ARRAY_ITEM_IN_QUOTES]
suspicious_keywords = [THIRD_ARRAY_ITEM]

# Used to compare the structures of extracted contents
class ComparablePattern(BaseModel):
    pattern: re.Pattern
    is_identical: Callable[[str, str], bool]

# Most commonly used pattern
common_comparable_pattern = ComparablePattern(
    pattern=JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM, # Used to extract content
    is_identical=lambda x,y: comparator.compare_json_keys(json.loads(x), json.loads(y)) # Used to compare if two extacted contents have identical data structures
)

# A config map to link keyword and its content patterns
COMPARABLE_KEYWORD_CONTENT_MAP = {
    'authorize': [common_comparable_pattern],
    'bootnotification': [common_comparable_pattern],
    'datatransfer': [common_comparable_pattern],
    'heartbeat': [common_comparable_pattern],
    'metervalues': [common_comparable_pattern],
    'starttransaction': [common_comparable_pattern],
    'statusnotification': [common_comparable_pattern],
    'stoptransaction': [common_comparable_pattern],
}
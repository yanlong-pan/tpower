import json
import re
from typing import Callable, List


def compare_json_keys(json1, json2) -> bool:
    if isinstance(json1, dict) and isinstance(json2, dict):
        # Compare the keys of the dictionaries
        if set(json1.keys()) != set(json2.keys()):
            return False
        # Recursively compare the values for each key
        for key in json1:
            if not compare_json_keys(json1[key], json2[key]):
                return False
        return True
    elif isinstance(json1, list) and isinstance(json2, list):
        # Compare structure of lists
        if not json1 and not json2:
            return True  # Both lists are empty
        if (json1 and not json2) or (not json1 and json2):
            return False  # One list is empty and the other is not
        # Compare the structure of the first element in each list
        # As we assume the structures of items inside the same list are identical
        return compare_json_keys(json1[0], json2[0])
    else:
        # For non-dict and non-list types, return True (since only keys are compared)
        return True

def compare_value_structure(json1: dict, json2: dict, key, str_comparators: List[Callable[[str, str], bool]]) -> bool:
    if key in json1 and key in json2:
        # Both have value
        if json1[key] and json2[key]:
            # Any comparator passing indicates the values are identical
            for str_comparator in str_comparators:
                if str_comparator(json1[key], json2[key]):
                    return True
        # Both blank
        elif not json1[key] and not json2[key]:
            return True
    return False

def compare_query_strs(s1: str, s2: str):
    def _is_query_string_structure(query_string):
        # The regular expression matches a query string structure.
        pattern = re.compile(r'^(\w+=[^&]+)(?:&\w+=[^&]+)*$')
        return bool(pattern.match(query_string))

    def _parse_query_string(query_string):
        """Parses a query string into a dictionary of keys."""
        return {kv.split('=')[0] for kv in query_string.split('&')}

    if all(map(_is_query_string_structure, [s1, s2])):
        return _parse_query_string(s1) == _parse_query_string(s2)
    return False

def compare_json_string(s1: str, s2: str):
    try:
        json1, json2 = json.loads(s1), json.loads(s2)
        return compare_json_keys(json1, json2)
    except json.JSONDecodeError:
        return False

def datatransfer_content_comparator(s1: str, s2: str):
    json1, json2 = json.loads(s1), json.loads(s2)
    if compare_json_keys(json1, json2):
        str_comparators = [compare_query_strs, compare_json_string]
        return compare_value_structure(json1, json2, 'data', str_comparators)
    return False
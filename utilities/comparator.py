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
        return compare_json_keys(json1[0], json2[0])
    else:
        # For non-dict and non-list types, return True (since only keys are compared)
        return True

# TODO: remove
# Example JSON objects
json_obj1 = {
    "connectorId": 0,
    "errorCode": "NoError",
    "status": "Available",
    "timestamp": "2024-07-09T07:14:24Z",
    "details": {
        "location": "A1",
        "type": "fast",
        "extra": [ {"a": "a"}, {"a": "c"}]
    }
}

json_obj2 = {
    "connectorId": 1,
    "errorCode": "Error",
    "status": "Occupied",
    "timestamp": "2024-07-09T08:14:24Z",
    "details": {
        "location": "A2",
        "type": "slow",
        "extra": [ {"a": "a"}, {"a": "b"}]
    }
}

# Compare the two JSON objects
are_keys_equal = compare_json_keys(json_obj1, json_obj2)
print("Are JSON keys equal?", are_keys_equal)

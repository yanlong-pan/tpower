import re

THIRD_ARRAY_ITEM=re.compile(r'receive message \[\s*\d+\s*,\s*"[^"]+"\s*,(.+)\]')
THIRD_ARRAY_ITEM_IN_QUOTES=re.compile(r'receive message \[\s*\d+\s*,\s*"[^"]+"\s*,\s*"([^"]+)"')
JSON_CONTENT_AFTER_THIRD_ARRAY_ITEM=re.compile(r'receive message\s*\[.+,.+,\"\w+\",(\{.+\})[,|\]]')
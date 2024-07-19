import json
import re
import threading
import os

from scripts import patterns
from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the root path of the project directory
root_dir = os.path.dirname(current_dir)
# Create a thread lock
lock = threading.Lock()

# Constants
EXTRACTED_FILES_DIR_PATH = os.path.join(root_dir, 'statics/logs/extracted')
RAW_LOG_FILES_DIR_PATH = os.path.join(root_dir, 'statics/logs/raw')
CHARGER_SENT_MESSAGE_IDENTIFIER = 'receive message'

def extract_keywords_from_log(log_file_path):
    try:
        with open(log_file_path, 'r') as log_file:
            keywords_in_log = set()
            for line in log_file:
                if CHARGER_SENT_MESSAGE_IDENTIFIER in line:
                    # walk through all known keyword patterns
                    for keyword_pattern in patterns.keywords:
                        match = keyword_pattern.search(line)
                        if match:
                            keyword = match.group(1)
                            if keyword and keyword.isalpha():  # Check if the keyword is a word (contains only letters)
                                keywords_in_log.add(keyword)  # Will be used to match raw data, so we don't need to format it

                            # stop propagating once found a match
                            break
        
    except FileNotFoundError:
        print(f"Error: File {log_file_path} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    else:
        loggers.debug_file_logger.debug(f"Found keywords \'{keywords_in_log}\' in {log_file_path}")
        return keywords_in_log

def _extract_ocpp_charger_num(line):
    try:
        match = patterns.OCPP_CHARGER_NUM.search(line)
        num = match.group(1)
        return f'Ocpp charger number: {num}'
    except:
        return f'Ocpp charger number: Not found'

def extract_content_with_keyword_from_file(keyword: str, raw_log_filepath, output_path, multithread_result=None):
    is_success = True
    extracted_lines, total_lines = 0, 0
    # The former set simply stores content so that they can compare between each other,
    # while the latter set will store content with charger number concatenated
    unique_structure_content_examples, unique_example_with_charger_num = set(), set()
    comparable_content_patterns = patterns.COMPARABLE_KEYWORD_CONTENT_MAP[keyword.lower()]
    output_dir = os.path.dirname(output_path)
    # Create directories if non-exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(raw_log_filepath, 'r') as file, open(output_path, 'w') as output_file:
        for line in file:
            total_lines += 1
            try:
                if CHARGER_SENT_MESSAGE_IDENTIFIER in line and keyword in line:
                    output_file.write(line)
                    extracted_lines += 1
                    # extract content examples having unique data structures
                    for comparable_content_pattern in comparable_content_patterns:
                        match = comparable_content_pattern.pattern.search(line)
                        if match:
                            content = match.group(1)
                            if content:
                                if not unique_structure_content_examples:
                                    unique_structure_content_examples.add(content)
                                    unique_example_with_charger_num.add(f'{content}, {_extract_ocpp_charger_num(line)}')
                                else:
                                    is_unique = True
                                    for item in unique_structure_content_examples:
                                        is_unique = not comparable_content_pattern.is_identical(content, item) and is_unique
                                    if is_unique:
                                        unique_structure_content_examples.add(content)
                                        unique_example_with_charger_num.add(f'{content}, {_extract_ocpp_charger_num(line)}')
                            # Stop the iteration once a match is found no matter if it's unique
                            break
            except:
                is_success = False
                r = {
                    'keyword': keyword,
                    'line': line,
                }
                loggers.error_file_logger.error(json.dumps(r, indent=4), exc_info=True)

    summary = {
        'success': is_success,
        'keyword': keyword,
        'unique_example_with_charger_num': list(unique_example_with_charger_num),
        'extracted_lines': extracted_lines,
        'total_lines': total_lines,
        'input_filepath': raw_log_filepath,
        'output_filepath': output_path,
    }
    loggers.debug_file_logger.debug(json.dumps(summary, indent=4))
    # Store results when use multithreads
    if isinstance(multithread_result, list):
        with lock:
            multithread_result.append({
                keyword: summary
            })
    return summary

def _prepare_for_file_extractor():
    raw_log_filename = input(f"Please enter the log file name under '{RAW_LOG_FILES_DIR_PATH}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(RAW_LOG_FILES_DIR_PATH, raw_log_filename)

    kws = extract_keywords_from_log(log_file_path=raw_log_filepath)
    return kws, raw_log_filename, raw_log_filepath

# Process keyword one by one in a file
def single_threaded_log_file_extractor():
    keywords, raw_log_filename, raw_log_filepath = _prepare_for_file_extractor()
    res = {}
    for keyword in sorted(keywords):    
        output_path = os.path.join(EXTRACTED_FILES_DIR_PATH, keyword.lower(), f'from_{raw_log_filename}')
        r = extract_content_with_keyword_from_file(keyword, raw_log_filepath, output_path)
        res[keyword.lower()] = r
    return res

# Concurrently process all the keywords in a file
def multi_threaded_log_file_extractor():
    keywords, raw_log_filename, raw_log_filepath = _prepare_for_file_extractor()
    threads, multithread_result = [], []
    # Define a list of different parameters to pass
    parameters = [(
        keyword,
        raw_log_filepath, os.path.join(EXTRACTED_FILES_DIR_PATH, keyword.lower(),
        f'from_{raw_log_filename}'),
        multithread_result
    ) for keyword in sorted(keywords)]

    for param in parameters:
        # Create the target function for the thread
        thread = threading.Thread(target=extract_content_with_keyword_from_file, args=param)  # Use args to pass parameters to the thread's target function
        threads.append(thread) 
        thread.start()
    # Wait for all threads to complete
    for thread in threads:
        thread.join()  # Wait for each thread to finish
    return multithread_result

if __name__ == "__main__":
    # r = single_threaded_log_file_extractor()
    r = multi_threaded_log_file_extractor()

    def add_ocpp_num(input_json):
        key = 'unique_example_with_charger_num'
        
        # Handle both list of dictionaries and single dictionary
        if isinstance(input_json, list):
            for item in input_json:
                if isinstance(item, dict):
                    process_dictionary(item, key)
        elif isinstance(input_json, dict):
            process_dictionary(input_json, key)
        
        return input_json

    def process_dictionary(dictionary, key):
        """Process a dictionary to integrate Ocpp charger numbers."""
        for value in dictionary.values():
            if isinstance(value, dict) and key in value:
                updated_examples = []
                for example in value[key]:
                    # Split JSON obj and charger number
                    match = re.match(r'^(.*?}), Ocpp charger number: (\w+)$', example)
                    if match:
                        json_part = match.group(1)
                        charger_number = match.group(2)
                        # Parse JSON obj and add charger number
                        json_object = json.loads(json_part)
                        json_object['charger_number'] = charger_number
                        json_object['original'] = json_part
                        updated_examples.append(json_object)
                value[key] = updated_examples

    with open(os.path.join(root_dir, 'output.json'), 'w', encoding='utf-8') as f:
        json.dump(add_ocpp_num(r), f, indent=4, ensure_ascii=False)

import json
import threading
import os
import traceback

from scripts import patterns
from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Create a thread lock
lock = threading.Lock()

def load_keywords(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, 'r') as file:
        return set(line.strip().lower() for line in file)

def save_keywords(keywords, file_path):
    with open(file_path, 'w') as file:
        for keyword in sorted(keywords):
            file.write(f"{keyword.strip().lower()}\n")

def extract_keywords_from_log(log_file_path, known_keywords_path, suspicious_keywords_path):
    
    known_keywords = load_keywords(known_keywords_path)
    suspicious_keywords = load_keywords(suspicious_keywords_path)
    
    try:
        with open(log_file_path, 'r') as log_file:
            keywords_in_log = set()
            for line_num, line in enumerate(log_file, start=1):
                if 'receive message' in line:
                    found_keyword = False
                    # walk through all known keyword patterns
                    for keyword_pattern in patterns.keywords:
                        match = keyword_pattern.search(line)
                        if match:
                            keyword = match.group(1)
                            if keyword and keyword.isalpha():  # Check if the keyword is a word (contains only letters)
                                formatted_kw = keyword.strip().lower()
                                keywords_in_log.add(keyword)  # Will be used to match raw data, so we don't need to format it
                                if formatted_kw not in known_keywords:
                                    known_keywords.add(formatted_kw)
                                    loggers.debug_file_logger.debug(f'Found a new keyword \'{keyword}\' in line {line_num} within {log_file_path}')
                            # stop propagating once found a match
                            found_keyword = True
                            break
                    # walk through all suspicious keyword patterns if no known keyword is found
                    if not found_keyword:      
                        for suspicious_keyword_pattern in patterns.suspicious_keywords:
                            match = suspicious_keyword_pattern.search(line)
                            if match:
                                suspicious_keyword = match.group(1)
                                if suspicious_keyword:
                                    formatted_suspicious_kw = suspicious_keyword.strip().lower()
                                    if formatted_suspicious_kw not in suspicious_keywords:
                                        suspicious_keywords.add(formatted_suspicious_kw)
                                        loggers.debug_file_logger.debug(f'Found a new suspicious keyword \'{suspicious_keyword}\' in line {line_num} within {log_file_path}')
                                break
        
    except FileNotFoundError:
        print(f"Error: File {log_file_path} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    else:
        save_keywords(known_keywords, known_keywords_path)
        save_keywords(suspicious_keywords, suspicious_keywords_path)
        loggers.debug_file_logger.debug(f"Found keywords \'{keywords_in_log}\' in {log_file_path}")
        return keywords_in_log

def _extract_ocpp_charger_num(line):
    try:
        match = patterns.OCPP_CHARGER_NUM.search(line)
        num = match.group(1)
        return f'Ocpp charger number: {num}'
    except:
        return f'Ocpp charger number: Not found'

def extract_content_with_keyword(keyword: str, raw_log_filepath, output_path, multithread_result=None):
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
                if keyword in line:
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
                    'error': f'An error occurred: {traceback.format_exc()}'
                }
                loggers.error_file_logger.error(r)

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
    return r

def _prepare_for_file_extractor():
    root_dir = os.path.dirname(current_dir)
    raw_logs_dir_path = os.path.join(root_dir, 'statics/logs/raw')
    raw_log_filename = input(f"Please enter the log file name under '{raw_logs_dir_path}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(raw_logs_dir_path, raw_log_filename)

    kws = extract_keywords_from_log(
        log_file_path=raw_log_filepath,
        known_keywords_path=os.path.join(root_dir, 'statics/keywords.txt'),
        suspicious_keywords_path=os.path.join(root_dir, 'statics/keywords_suspicious.txt')
    )
    return kws, root_dir, raw_log_filename, raw_log_filepath

# Process keyword one by one in a file
def single_threaded_log_file_extractor():
    keywords, root_dir, raw_log_filename, raw_log_filepath = _prepare_for_file_extractor()
    res = {}
    for keyword in sorted(keywords):    
        output_path = os.path.join(root_dir, 'statics/logs/extracted', keyword.lower(), f'from_{raw_log_filename}')
        r = extract_content_with_keyword(keyword, raw_log_filepath, output_path)
        res[keyword.lower()] = r['data']
    return res

# Concurrently process all the keywords in a file
def multi_threaded_log_file_extractor():
    keywords, root_dir, raw_log_filename, raw_log_filepath = _prepare_for_file_extractor()
    threads, multithread_result = [], []
    # Define a list of different parameters to pass
    parameters = [(
        keyword,
        raw_log_filepath, os.path.join(root_dir, 'statics/logs/extracted', keyword.lower(),
        f'from_{raw_log_filename}'),
        multithread_result
    ) for keyword in sorted(keywords)]

    for param in parameters:
        # Create the target function for the thread
        thread = threading.Thread(target=extract_content_with_keyword, args=param)  # Use args to pass parameters to the thread's target function
        threads.append(thread) 
        thread.start()
    # Wait for all threads to complete
    for thread in threads:
        thread.join()  # Wait for each thread to finish
    return multithread_result

if __name__ == "__main__":
    # r = single_threaded_log_file_extractor()
    r = multi_threaded_log_file_extractor()
    print(json.dumps(r, indent=4))
    pass
    

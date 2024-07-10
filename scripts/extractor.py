import json
import os
import re

from scripts import patterns
from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

def load_keywords(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, 'r') as file:
        return set(line.strip() for line in file)

def save_keywords(keywords, file_path):
    with open(file_path, 'w') as file:
        for keyword in sorted(keywords):
            file.write(f"{keyword}\n")

def extract_keywords_from_log(log_file_path, known_keywords_path, suspicious_keywords_path):
    keyword_patterns = [patterns.THIRD_ARRAY_ITEM_IN_QUOTES]
    suspicious_keyword_patterns = [patterns.THIRD_ARRAY_ITEM]
    
    known_keywords = load_keywords(known_keywords_path)
    suspicious_keywords = load_keywords(suspicious_keywords_path)
    
    try:
        with open(log_file_path, 'r') as log_file:
            for line_num, line in enumerate(log_file, start=1):
                if 'receive message' in line:
                    found_keyword = False
                    # walk through all known keyword patterns
                    for keyword_pattern in keyword_patterns:
                        match = keyword_pattern.search(line)
                        if match:
                            keyword = match.group(1)
                            if keyword.isalpha():  # Check if the keyword is a word (contains only letters)
                                if keyword not in known_keywords:
                                    known_keywords.add(keyword)
                                    loggers.debug_file_logger.debug(f'Found a new keyword \'{keyword}\' in line {line_num} within {log_file_path}')
                                # TODO: save the current line data into the corresponding keyword file
                            # stop propagating once found a match
                            found_keyword = True
                            break
                    # walk through all suspicious keyword patterns if no known keyword is found
                    if not found_keyword:      
                        for suspicious_keyword_pattern in suspicious_keyword_patterns:
                            match = suspicious_keyword_pattern.search(line)
                            if match:
                                suspicious_keyword = match.group(1)
                                if suspicious_keyword and suspicious_keyword not in suspicious_keywords:
                                    suspicious_keywords.add(suspicious_keyword)
                                    loggers.debug_file_logger.debug(f'Found a new suspicious keyword \'{suspicious_keyword}\' in line {line_num} within {log_file_path}')
                                # stop propagating once found a match
                                break
        
    except FileNotFoundError:
        print(f"Error: File {log_file_path} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        save_keywords(known_keywords, known_keywords_path)
        save_keywords(suspicious_keywords, suspicious_keywords_path)


def extract_meter_values():
    raw_logs_dir_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/raw')
    raw_log_filename = input(f"Please enter the log file name under '{raw_logs_dir_path}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(raw_logs_dir_path, raw_log_filename)
    keyword = input("Please enter the keyword to search for (default is 'MeterValues'): ") or "MeterValues"

    # load keywords

    # Generate the absolute path for the output file
    output_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/extracted', f'meter_values_from_{raw_log_filename}')

    try:
        extracted_lines, total_lines = 0, 0
        with open(raw_log_filepath, 'r') as file, open(output_path, 'w') as output_file:
            for line in file:
                total_lines += 1
                if keyword in line:
                    output_file.write(line)
                    extracted_lines += 1
        r = {
            'success': True,
            'data': {
                'keyword': keyword,
                'extracted_lines': extracted_lines,
                'total_lines': total_lines,
                'input_filepath': raw_log_filepath,
                'output_filepath': output_path,
            }
        }
        loggers.debug_file_logger.debug(json.dumps(r, indent=4))
        return r
    except FileNotFoundError:
        r = {
            'success': False,
            'error': f'Error: File {raw_log_filepath} not found.'
        }
        loggers.error_file_logger.error(json.dumps(r, indent=4))
        return r
    except Exception as e:
        r = {
            'success': False,
            'error': f'An error occurred: {e}'
        }
        loggers.error_file_logger.error(json.dumps(r, indent=4))
        return r

if __name__ == "__main__":
    # Run the extraction function
    # r = extract_meter_values()
    # print(json.dumps(r, indent=4))
    extract_keywords_from_log(
        log_file_path='/Users/panyanlong/workspace/tpower/statics/logs/raw/log1.log',
        known_keywords_path='/Users/panyanlong/workspace/tpower/statics/keywords.txt',
        suspicious_keywords_path='/Users/panyanlong/workspace/tpower/statics/keywords_suspicious.txt'
    )

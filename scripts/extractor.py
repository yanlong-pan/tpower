import json
import threading
import os

from scripts import patterns
from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))
# 创建线程锁
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


def extract_content_with_keyword(keyword: str, raw_log_filepath, output_path, multithread_result=None):
    try:
        extracted_lines, total_lines = 0, 0
        unique_structure_content_examples = set()
        comparable_content_patterns = patterns.COMPARABLE_KEYWORD_CONTENT_MAP[keyword.lower()]
        output_dir = os.path.dirname(output_path)
        # Create directories if non-exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(raw_log_filepath, 'r') as file, open(output_path, 'w') as output_file:
            for line in file:
                total_lines += 1
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
                                else:
                                    is_unique = True
                                    for item in unique_structure_content_examples:
                                        is_unique = not comparable_content_pattern.is_identical(content, item) and is_unique
                                    if is_unique:
                                        unique_structure_content_examples.add(content)
                            # Stop the iteration once a match is found no matter if it's unique
                            break
                    
        summary = {
            'unique_structure_content_examples': list(unique_structure_content_examples),
            'extracted_lines': extracted_lines,
            'total_lines': total_lines,
            'input_filepath': raw_log_filepath,
            'output_filepath': output_path,
        }
        r = {
            'success': True,
            'data': {'keyword': keyword, **summary}
        }
        loggers.debug_file_logger.debug(json.dumps(r, indent=4))
        if isinstance(multithread_result, list):
            with lock:
                multithread_result.append({
                    keyword: summary
                })
        return r
    except FileNotFoundError:
        r = {
            'success': False,
            'error': f'Error: File {raw_log_filepath} not found.'
        }
        loggers.error_file_logger.error(json.dumps(r, indent=4))
        if isinstance(multithread_result, list):
            with lock:
                multithread_result.append(r)
        return r
    except Exception as e:
        r = {
            'success': False,
            'error': f'An error occurred: {e}'
        }
        loggers.error_file_logger.error(json.dumps(r, indent=4))
        if isinstance(multithread_result, list):
            with lock:
                multithread_result.append(r)
        return r

if __name__ == "__main__":
    # TODO: put into a function
    raw_logs_dir_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/raw')
    raw_log_filename = input(f"Please enter the log file name under '{raw_logs_dir_path}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(raw_logs_dir_path, raw_log_filename)

    kws = extract_keywords_from_log(
        log_file_path=raw_log_filepath,
        known_keywords_path='/Users/panyanlong/workspace/tpower/statics/keywords.txt',
        suspicious_keywords_path='/Users/panyanlong/workspace/tpower/statics/keywords_suspicious.txt'
    )

# # 单线程
#     res = {}
#     for keyword in sorted(kws):    
#         output_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/extracted', keyword.lower(), f'from_{raw_log_filename}')
#         r = extract_content_with_keyword(keyword, raw_log_filepath, output_path)
#         res[keyword.lower()] = r['data']
#     print(json.dumps(res, indent=4))


# 多线程
    # 创建线程列表
    threads = []
    multithread_result = []
    # 定义要传入的不同参数列表
    parameters = [(keyword,raw_log_filepath, os.path.join(os.path.dirname(current_dir), 'statics/logs/extracted', keyword.lower(), f'from_{raw_log_filename}'), multithread_result) for keyword in sorted(kws)]
    for param in parameters:
        # 创建线程目标函数
        thread = threading.Thread(target=extract_content_with_keyword, args=param)  # 使用args传递参数给线程目标函数
        threads.append(thread)  # 将线程添加到列表中
        thread.start()  # 启动线程

    # 等待所有线程完成
    for thread in threads:
        thread.join()  # 等待每个线程结束

    print(json.dumps(multithread_result, indent=4))

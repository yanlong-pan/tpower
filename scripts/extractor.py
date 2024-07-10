import json
import os

from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

def extract_meter_values():
    raw_logs_dir_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/raw')
    raw_log_filename = input(f"Please enter the log file name under '{raw_logs_dir_path}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(raw_logs_dir_path, raw_log_filename)
    keyword = input("Please enter the keyword to search for (default is 'MeterValues'): ") or "MeterValues"

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
    r = extract_meter_values()
    print(json.dumps(r, indent=4))

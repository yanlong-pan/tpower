import os

from utilities import loggers

# Get the current script directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

def extract_meter_values():
    raw_logs_dir_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/raw')
    raw_log_filename = input(f"Please enter the log file name under '{raw_logs_dir_path}' (eg. log1.log): ")
    raw_log_filepath = os.path.join(raw_logs_dir_path, raw_log_filename)
    keyword = 'MeterValues'

    # Generate the absolute path for the output file
    output_path = os.path.join(os.path.dirname(current_dir), 'statics/logs/extracted', f'meter_values_from_{raw_log_filename}')

    try:
        extracted_lines = 0
        with open(raw_log_filepath, 'r') as file, open(output_path, 'w') as output_file:
            for line in file:
                if keyword in line:
                    output_file.write(line)
                    extracted_lines += 1
        loggers.debug_file_logger.debug(f'Extracted content ({extracted_lines} lines) has been saved to: {output_path}')
    except FileNotFoundError:
        loggers.error_file_logger.error(f'Error: File {raw_log_filepath} not found.')
    except Exception as e:
        loggers.error_file_logger.error(f'An error occurred: {e}')

if __name__ == "__main__":
    # Run the extraction function
    extract_meter_values()

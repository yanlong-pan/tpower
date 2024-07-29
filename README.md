# 1. Project Overview

This project consists of two main parts: a Python script for extracting log text data and a Django backend for log data analysis.

# 2. Log Extraction Script

The primary task is to filter specific formatted data from various offline log files and save it to a file while outputting statistical information in a specified format.

### Example:

- Filter lines containing the keywords "receive message" and "MeterValues" from the file `log1.log`.
- Save the filtered lines to the directory `statics/logs/extracted/metervalues`, e.g., `from_log1.log`.
- Output statistical information in the shell, such as:

```json
{
    "success": true,
    "keyword": "DataTransfer",
    "unique_example_with_charger_num": [
        "{\"data\":\"{\\\"FaultGroup\\\":[{\\\"connectorId\\\":1,\\\"fault\\\":[{\\\"Reason\\\":\\\"charging plug is not home\\\"}]},{\\\"connectorId\\\":2,\\\"fault\\\":[{\\\"Reason\\\":\\\"charging plug is not home\\\"}]}],\\\"timestamp\\\":\\\"2024-07-24T01:41:22Z\\\"}\",\"messageId\":\"chargePoridStatu\",\"vendorId\":\"CEGN\"}, Ocpp charger number: TH009",
        "{\"data\":\"{\\\"FaultGroup\\\":[],\\\"timestamp\\\":\\\"2024-07-24T01:41:49Z\\\"}\",\"messageId\":\"chargePoridStatu\",\"vendorId\":\"CEGN\"}, Ocpp charger number: TH009"
    ],
    "extracted_lines": 7,
    "total_lines": 56,
    "input_filepath": "~/tpower/statics/logs/raw/log1.log",
    "output_filepath": "~/tpower/statics/logs/extracted/datatransfer/from_log1.log"
}
```
- Save the beautified output to output.json.

## 2.1 How to Run
After pulling the code, navigate to the project's root directory from the shell. It is recommended to create a Python virtual environment, then follow these steps:

- Place the log files to be extracted under the `statics/logs/raw` path
- Run `pip install -r requirements.txt`.
- Set the environment variable: `export PYTHONPATH=$(pwd)`.
- Run `python scripts/extractor.py`.
- Enter the filename when prompted, e.g., `log1.log`.
- Check the shell output and view `output.json`.

# 3 Django backend 

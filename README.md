<!-- toc -->

- [1. Project Overview](#1-project-overview)
- [2. Log Extraction Script](#2-log-extraction-script)
  - [Example](#example)
  - [2.1 How to Run](#21-how-to-run)
  - [2.2 Core Implementation](#22-core-implementation)
- [3. Django Backend](#3-django-backend)
  - [3.1 Main Tasks](#31-main-tasks)
  - [3.2 Main Technical Stack](#32-main-technical-stack)
  - [3.3 Database](#33-database)
    - [3.3.1 ER Diagram](#331-er-diagram)
    - [3.3.2 Table Examples](#332-table-examples)
  - [3.4 How to Run](#34-how-to-run)
  - [3.5 Core Concepts](#35-core-concepts)
    - [Parsing Rules for MeterValues Request Type](#parsing-rules-for-metervalues-request-type)
- [4. Logging System](#4-logging-system)
- [5. Testing](#5-testing)

<!-- tocstop -->

# 1. Project Overview

This project consists of two main parts: a Python script for extracting log text data and a Django backend for log data analysis.

# 2. Log Extraction Script

The primary task is to filter specific formatted data from various offline log files and save it to a file while outputting statistical information in a specified format.

## Example

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

## 2.2 Core Implementation

1. The script first extracts all keywords (request types) from the file using regular expressions.
2. It uses multithreading, with each keyword corresponding to a thread. Each thread reads the file and filters out log records that do not meet the criteria.
3. To determine if a log record has a unique structure, a custom comparator is used. The main logic includes comparing the key-value structures of two JSON objects, comparing the structures of all elements in a list, and comparing specific structures of designated key-values. For detailed implementation, please refer to `utilities/comparator.py` and the `COMPARABLE_KEYWORD_CONTENT_MAP` in `scripts/patterns.py`.

# 3. Django Backend

## 3.1 Main Tasks

1. Standardize the user input into a unified format regardless of their specific formats, involving parsing, validating, and transforming the raw data to ensure consistency.
2. After the raw data is parsed, store standardized data in a relational database.
3. Return the parsed, formatted data to the frontend for display.
4. Implement a robust logging system with a standardized log file format.
5. Conduct thorough testing to ensure the platform functions correctly and reliably.

## 3.2 Main Technical Stack

- Python 3.9+
- Django 3.2
- djangorestframework 3.12.4
- SQLite

For more information, please refer to `requirements.txt`.

## 3.3 Database

### 3.3.1 ER Diagram

![image](https://github.com/user-attachments/assets/6a4d5ad3-f748-44bc-a40b-f7851eab1afc)

### 3.3.2 Table Examples

- Table: `log_processor_sampledmetervalue`
  - Columns: `id`, `charger_number`, `connector_id`, `transaction_id`, `L1`, `L2`, `L3`, `raw_data`
    ![image](https://github.com/user-attachments/assets/036c0045-52cb-4d14-a7ec-b10d74a6a48f)

- Table: `log_processor_datatransferrequest`
  - Columns: `id`, `charger_number`, `vendor_id`, `message_id`, `data`, `raw_data`
    ![image](https://github.com/user-attachments/assets/dc672a7d-d332-430e-bed2-2ba78724da54)

## 3.4 How to Run

After pulling the code, navigate to the project's root directory from the shell. It is recommended to create a Python virtual environment, then follow these steps:

1. Check the `CORS_ALLOWED_ORIGINS` field in the `ocpp_log_sys/settings.py` file to ensure the port number matches the local frontend instance.
2. Run `python manage.py makemigrations`.
3. Run `python manage.py migrate`.
4. Run `python manage.py runserver 3000`.

Ensure the specific port number (3000 in this case) matches the request port number configured in the frontend files.

## 3.5 Core Concepts

User input undergoes parsing, validating, and storing. Below is a brief explanation of each step:

- Use regular expressions to extract the charger number, request type, and request content.
- Match the request type to a Parser, each of which can define a series of steps where each subsequent step uses the output of the previous step. For example, the `metervalues` Parser includes the steps: `[add_charger_number_and_raw_data_to_content, flatten_meter_value, process_sampled_values]`. The Parser processes the request content and outputs a series of data objects along with a DRF Serializer class for data validation.
- The Serializer validates each parsed data object, and upon successful validation, stores it in the database.

Each step includes exception handling.

### Parsing Rules for MeterValues Request Type

The `metervalues` request usually contains numerous sampledValues. Since not all samples are of interest, the following rules are applied:

1. Retain only samples with positive values.
2. Retain only samples where the unit is one of 'V', 'Wh', 'W', or 'A'.
3. If the sample lacks a phase field or the field is empty, treat it as an overall value and set phase to L1.
4. If multiple samples of the same type exist (same except for "value", "phase", "timestamp"):
    - Retain the overall value sample if it exists.
    - If three-phase samples exist, retain one set according to the priority: "L1, L2, L3" > "L1-N, L2-N, L3-N" > "L1-L2, L2-L3, L3-L1". For example, if samples with phases "L1, L2, L3" and "L1-N, L2-N, L3-N" both exist, retain only the set with phases "L1, L2, L3".
5. For single-phase samples, treat them all as phase L1, regardless of whether their phase is "L1, L2, L3, L1-N, L2-N, L3-N, L1-L2, L2-L3, L3-L1".

# 4. Logging System

In the `loggers.py` file, three logger instances are defined: `debug_file_logger`, `error_file_logger`, and `test_logger`.
![image](https://github.com/user-attachments/assets/91079961-f0e5-473a-974d-c2e49d9219c8)

- `debug_file_logger` and `error_file_logger`:
  - These loggers output log information to the shell and save it to files (split by date).
  - They remain disabled in testing scenarios to avoid cluttering with irrelevant log information.

- `test_logger`:
  - This logger is used exclusively for testing scenarios.
  - It outputs log information only to the shell.

# 5. Testing

All tests are defined in the `log_processor/tests.py` file. To run all test instances, use the following command:

```sh
python manage.py test
```

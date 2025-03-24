import re

def extract_processed_zip_codes(log_file_path):
    """
    Reads a log file and extracts an array of zip codes that were processed.

    Args:
        log_file_path (str): The path to the log file.

    Returns:
        list: A list of zip codes that were processed, or an empty list if none were found.
    """
    processed_zip_codes = []
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                # Check for the "Extracting data for ZIP code:" pattern
                match = re.search(r"Extracting data for ZIP code: (\d+)", line)
                if match:
                    zip_code = match.group(1)
                    processed_zip_codes.append(zip_code)
    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file_path}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    return processed_zip_codes


# Example usage with the provided log file path:
import sys
import os
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)
log_file = os.path.join(project_dir, "logs", "bizlist.log")
zip_codes = extract_processed_zip_codes(log_file)

if zip_codes:
    print(zip_codes)
else:
    print("No zip codes were found in the log file.")

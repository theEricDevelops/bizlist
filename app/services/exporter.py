import csv
import os
import time
from typing import List
from app.core.config import config
from app.services.logger import Logger

log = Logger('service-exporter')


class Exporter:
    def __init__ (self):
        pass

    def to_csv(self, data: List[any], filename: str = None) -> str:
        """Exports data to a CSV file."""
        if not filename:
            filename = f"export_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(config.download_dir, filename)
        log.debug(f"Exporting data to CSV: {filepath}")

        try:
            with open(filepath,
                    mode='w',
                    newline='') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            log.info(f"Data exported to CSV: {filename}")
        except Exception as e:
            log.exception(f"An unexpected error occurred while exporting data to CSV: {e}")
            return None
        return filename
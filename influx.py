from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import logging
from typing import List, Optional

class InfluxConnector:
    def __init__(self, bucket: str, token: str, org: str, url: str, measurement: str):
        self.bucket: str = bucket
        self.token: str = token
        self.org: str = org
        self.url: str = url
        self.measurement: str = measurement

    def __get_client(self) -> InfluxDBClient:
        """Initialize and return an InfluxDB client."""
        return InfluxDBClient(url=self.url, token=self.token, org=self.org, debug=False)

    def get_last_recorded_time(self, max_days: int, to_time: datetime) -> datetime:
        """
        Retrieve the timestamp of the last recorded data point.
        If no record is found, return a timestamp `max_days` ago from `to_time`.
        """
        try:
            logging.info(f"Fetching last recorded time for measurement '{self.measurement}' in bucket '{self.bucket}'.")
            query = f'from(bucket: "{self.bucket}") |> range(start: -{max_days}d) |> filter(fn: (r) => r._measurement == "{self.measurement}") |> last()'
            result = self.__run_query(query)
            results = list(result)

            if not results:
                logging.info(f"No records found for the last {max_days} day(s) in bucket '{self.bucket}', measurement '{self.measurement}'.")
                return to_time - timedelta(days=max_days)

            fluxtable = results[-1]
            fluxrecord = fluxtable.records[-1]
            fluxtime = fluxrecord.get_time()

            logging.info(f"Last recorded time found: {fluxtime}")
            return fluxtime

        except Exception as e:
            logging.exception(f"Error while querying last recorded time: {e}")
            raise

    def add_samples(self, records: List[dict]) -> None:
        """Add a list of records to the InfluxDB."""
        if not records:
            logging.info("No records to import.")
            return

        logging.info(f"Importing {len(records)} record(s) to InfluxDB.")
        try:
            with self.__get_client() as client:
                with client.write_api() as write_api:
                    write_api.write(bucket=self.bucket, record=records)
            logging.info(f"Successfully imported {len(records)} record(s).")
        except Exception as e:
            logging.exception(f"Error writing data to InfluxDB: {e}")
            raise

    def __run_query(self, query: str) -> Optional[List]:
        """
        Run a Flux query and return the results.
        """
        logging.info(f"Running query: {query}")
        try:
            with self.__get_client() as client:
                query_api = client.query_api()
                result = query_api.query(query)
                return result
        except Exception as e:
            logging.exception(f"Error running query: {e}")
            raise

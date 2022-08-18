from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import logging


class InfluxConnector:
    def __init__(self, bucket: str, token: str, org: str, url: str, measurement: str):
        self.bucket: str = bucket
        self.token: str = token
        self.org: str = org
        self.url: str = url
        self.measurement: str = measurement

    def __get_client(self) -> InfluxDBClient:
        return InfluxDBClient(url=self.url, token=self.token, org=self.org, debug=False)

    def get_last_recorded_time(self, max_days: int, to_time: datetime) -> datetime:
        query = f'from(bucket: "{self.bucket}") |> range(start: -{max_days}d) |> filter(fn: (r) => r._measurement == "{self.measurement}") |> last()'
        result = self.__run_query(query)
        results = list(result)

        if len(results) == 0:
            logging.info(f"Found no records dated less than {max_days} days(s) in influx bucket {self.bucket} measurement {self.measurement}.")
            return to_time - timedelta(days=max_days)

        fluxtable = results[-1]
        fluxrecord = fluxtable.records[-1]
        fluxtime = fluxrecord.get_time()

        return fluxtime

    def add_samples(self, records: list) -> None:
        if len(records) < 1:
            return

        logging.info(f"Importing {len(records)} record(s) to influx.")
        with self.__get_client() as client:
            with client.write_api() as write_api:
                write_api.write(bucket=self.bucket, record=records)

    def __run_query(self, query) -> None:
        with self.__get_client() as client:
            query_api = client.query_api()
            return query_api.query(query)

import aiohttp
from asyncio.proactor_events import _ProactorBasePipeTransport
from datetime import datetime
from functools import wraps
import logging
from myair_client.client import MyAirConfig
from myair_client import get_client

# Code copied from
# https://pythonalgos.com/runtimeerror-event-loop-is-closed-asyncio-fix
"""fix yelling at me error"""


def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != 'Event loop is closed':
                raise
    return wrapper


_ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
"""fix yelling at me error end"""


class MyAirConnector:

    def __init__(self, config: dict[str, str]):
        self.config = MyAirConfig(username=config["login"], password=config["password"], region=config["region"])

    async def get_samples(self, last_report_time: str, from_time: datetime, to_time: datetime, measurement: str) -> list:
        try:
            client_session = aiohttp.ClientSession()
            client = get_client(self.config, client_session)
            await client.connect()
            device = await client.get_user_device_data()
            current_report_time = device['lastSleepDataReportTime']
            if last_report_time and last_report_time == current_report_time:
                await client_session.close()
                logging.info("No new data to import.")
                return None

            logging.info(f"Device last reported data on: {current_report_time}")
            tags = {k: v for k, v in device.items() if k in {'serialNumber', 'deviceType', 'localizedName'}}

            sleep_records = await client.get_sleep_records(from_time, to_time)

            ret = []
            for record in sleep_records:
                fields = {k: v for k, v in record.items() if k not in {'startDate', '__typename', 'sleepRecordPatientId'}}
                time = record["startDate"]
                logging.info(f"Record date: {time}")
                ret.append({"measurement": measurement, "tags": tags, "fields": fields, "time": time})

            await client_session.close()

            return [current_report_time, ret]

        except:
            logging.exception("Unable to get myair data")
            raise

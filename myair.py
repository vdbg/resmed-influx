import aiohttp
from asyncio.proactor_events import _ProactorBasePipeTransport
from datetime import datetime
from functools import wraps
import logging
from myair_client.client import MyAirConfig
from myair_client import get_client
from typing import List, Optional, Tuple, Dict

# Silence "Event loop is closed" error
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

class MyAirConnector:

    def __init__(self, config: Dict[str, str]):
        self.config = MyAirConfig(username=config["login"], password=config["password"], region=config["region"])

    async def get_samples(
        self, 
        last_report_time: Optional[str], 
        from_time: datetime, 
        to_time: datetime, 
        measurement: str
    ) -> Optional[Tuple[str, List[Dict]]]:
        try:
            async with aiohttp.ClientSession() as client_session:
                client = get_client(self.config, client_session)
                async with client:
                    await client.connect()
                    device = await client.get_user_device_data()
                    
                    current_report_time = device.get('lastSleepDataReportTime')
                    if last_report_time and last_report_time == current_report_time:
                        logging.info("No new data to import.")
                        return None

                    logging.info(f"Device last reported data on: {current_report_time}")
                    
                    tags = {k: v for k, v in device.items() if k in {'serialNumber', 'deviceType', 'localizedName'}}
                    sleep_records = await client.get_sleep_records(from_time, to_time)

                    results = []
                    for record in sleep_records:
                        fields = {k: v for k, v in record.items() if k not in {'startDate', '__typename', 'sleepRecordPatientId'}}
                        time = record.get("startDate")
                        logging.info(f"Record date: {time}")
                        results.append({
                            "measurement": measurement, 
                            "tags": tags, 
                            "fields": fields, 
                            "time": time
                        })

                    return current_report_time, results

        except aiohttp.ClientError as e:
            logging.error(f"HTTP Error: {e}")
            raise
        except Exception as e:
            logging.exception("Unexpected error occurred while getting myair data")
            raise

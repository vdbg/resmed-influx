import asyncio
from datetime import datetime, timezone
import logging
import platform
import sys
import time
import signal

from config import Config
from influx import InfluxConnector
from myair import MyAirConnector

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

last_report_time: str = None

SUPPORTED_PYTHON_MAJOR = 3
SUPPORTED_PYTHON_MINOR = 11

if sys.version_info < (SUPPORTED_PYTHON_MAJOR, SUPPORTED_PYTHON_MINOR):
    raise Exception(
        f"Python version {SUPPORTED_PYTHON_MAJOR}.{SUPPORTED_PYTHON_MINOR} or later required. Current version: {platform.python_version()}."
    )

async def main_loop(config):
    global last_report_time

    main_conf = config["main"]
    logging.getLogger().setLevel(logging.getLevelName(main_conf["logverbosity"]))
    sleep_time = main_conf["loop_minutes"] * 60
    logging.debug(f"CONFIG: {config}")

    my_air_conf = config["resmed"]
    my_air = MyAirConnector(my_air_conf)
    influx_conf = config["influx"]
    influx_connector = InfluxConnector(
        influx_conf["bucket"],
        influx_conf["token"],
        influx_conf["org"],
        influx_conf["url"],
        influx_conf["measurement"],
    )

    while True:
        try:
            logging.info("Starting data retrieval cycle.")
            to_time = datetime.now(timezone.utc)
            from_time = influx_connector.get_last_recorded_time(
                my_air_conf["max_days"], to_time
            )

            result = await my_air.get_samples(
                last_report_time, from_time, to_time, influx_connector.measurement
            )

            if result:
                logging.info("New data found, adding to InfluxDB.")
                influx_connector.add_samples(result[1])
                last_report_time = result[0]
            else:
                logging.info("No new data to add.")

        except Exception as e:
            logging.exception(f"Error in data retrieval or processing: {e}")

        if not sleep_time:
            logging.info("Sleep time is 0, exiting loop.")
            break

        logging.info(f"Sleeping for {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

def signal_handler(signal_received, frame):
    logging.info(f"Signal {signal_received} received, exiting gracefully.")
    sys.exit(0)

def main():
    try:
        config = Config("config.toml", "myair_influx").load()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logging.info("Starting main event loop.")
        asyncio.run(main_loop(config))

    except Exception as e:
        logging.exception(f"Critical error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import asyncio
from datetime import datetime, timezone
import logging
import platform
import sys
import time

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

try:
    config = Config("config.toml", "myair_influx").load()
    main_conf = config["main"]
    logging.getLogger().setLevel(logging.getLevelName(main_conf["logverbosity"]))
    sleep_time = main_conf["loop_minutes"] * 60
    logging.debug(f"CONFIG: {config}")

    my_air_conf = config["resmed"]
    my_air = MyAirConnector(my_air_conf)
    influx_conf = config["influx"]
    influxConnector = InfluxConnector(
        influx_conf["bucket"],
        influx_conf["token"],
        influx_conf["org"],
        influx_conf["url"],
        influx_conf["measurement"],
    )

    while True:
        try:
            to_time = datetime.now(timezone.utc)
            from_time = influxConnector.get_last_recorded_time(
                my_air_conf["max_days"], to_time
            )

            ret = asyncio.run(
                my_air.get_samples(
                    last_report_time, from_time, to_time, influxConnector.measurement
                )
            )
            if ret:
                influxConnector.add_samples(ret[1])
                last_report_time = ret[0]
        except Exception as e:
            logging.exception(e)

        if not sleep_time:
            exit(0)

        time.sleep(sleep_time)

except Exception as e:
    logging.exception(e)
    exit(1)

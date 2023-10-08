import os
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import platform
import sys
import time
import tomllib

from influx import InfluxConnector
from myair import MyAirConnector

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
CONFIG_FILE='config.toml'

def create_config():
    config_data = {
        "resmed": {
            "login": os.getenv('RESMED_LOGIN'),
            "password": os.getenv('RESMED_PASSWORD'),
            "region": os.getenv('RESMED_REGION'),
            "max_days": int(os.getenv('RESMED_MAX_DAYS', '365'))  # Default to 365 if not set
        },
        "influx": {
            "url": os.getenv('INFLUX_URL'),
            "bucket": os.getenv('INFLUX_BUCKET'),
            "measurement": os.getenv('INFLUX_MEASUREMENT'),
            "token": os.getenv('INFLUX_TOKEN'),
            "org": os.getenv('INFLUX_ORG')
        },
        "main": {
            "logverbosity": os.getenv('MAIN_LOGVERBOSITY', 'INFO'),  # Default to INFO if not set
            "loop_minutes": int(os.getenv('MAIN_LOOP_MINUTES', '60'))  # Default to 60 if not set
        }
    }
    with open(Path(__file__).with_name(CONFIG_FILE), "w") as config_file:
        tomllib.dump(config_data, config_file)

def get_config(retry=False):
    config_path = Path(__file__).with_name(CONFIG_FILE)
    if config_path.is_dir():
        logging.error(f"{CONFIG_FILE} is a directory. Deleting and recreating it as a file...")
        config_path.rmdir()  # This will fail if the directory is not empty
        create_config()
        if not retry:
            return get_config(retry=True)
        else:
            logging.error(f"Failed to recreate {CONFIG_FILE}.")
            exit(2)

    try:
        with open(config_path, "rb") as config_file:
            config = tomllib.load(config_file)
            if not config or not all(section in config for section in {"resmed", "influx", "main"}):
                if not retry:
                    logging.error(f"Invalid or incomplete {CONFIG_FILE}. Recreating it...")
                    create_config()
                    return get_config(retry=True)
                else:
                    logging.error(f"Failed to recreate {CONFIG_FILE}.")
                    exit(2)
            return config
    except FileNotFoundError as e:
        logging.error(f"Missing {e.filename}. Creating a new one...")
        create_config()
        if not retry:
            return get_config(retry=True)
        else:
            logging.error(f"Failed to create {e.filename}.")
            exit(2)


last_report_time: str = None

SUPPORTED_PYTHON_MAJOR = 3
SUPPORTED_PYTHON_MINOR = 11

if sys.version_info < (SUPPORTED_PYTHON_MAJOR, SUPPORTED_PYTHON_MINOR):
    raise Exception(f"Python version {SUPPORTED_PYTHON_MAJOR}.{SUPPORTED_PYTHON_MINOR} or later required. Current version: {platform.python_version()}.")

try:
    config = get_config()
    main_conf = config["main"]
    logging.getLogger().setLevel(logging.getLevelName(main_conf["logverbosity"]))
    sleep_time = main_conf["loop_minutes"] * 60

    my_air_conf = config["resmed"]
    my_air = MyAirConnector(my_air_conf)
    influx_conf = config["influx"]
    influxConnector = InfluxConnector(influx_conf["bucket"], influx_conf["token"], influx_conf["org"], influx_conf["url"], influx_conf["measurement"])

    while True:
        try:
            to_time = datetime.now(timezone.utc)
            from_time = influxConnector.get_last_recorded_time(my_air_conf["max_days"], to_time)

            ret = asyncio.run(my_air.get_samples(last_report_time, from_time, to_time, influxConnector.measurement))
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

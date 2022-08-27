
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
import yaml

from influx import InfluxConnector
from myair import MyAirConnector

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

file = "config.yaml"
last_report_time: str = None

try:
    while True:
        with open(Path(__file__).with_name(file)) as config_file:
            config = yaml.safe_load(config_file)

            for section in ["resmed", "influx", "main"]:
                if section not in config:
                    raise ValueError(f"Invalid {file}. Section {section} required.")

            main_conf = config["main"]
            logging.getLogger().setLevel(logging.getLevelName(main_conf["logverbosity"]))
            sleep_time = main_conf["loop_minutes"] * 60

            my_air_conf = config["resmed"]
            my_air = MyAirConnector(my_air_conf)
            influx_conf = config["influx"]
            influxConnector = InfluxConnector(influx_conf["bucket"], influx_conf["token"], influx_conf["org"], influx_conf["url"], influx_conf["measurement"])
            to_time = datetime.now(timezone.utc)
            from_time = influxConnector.get_last_recorded_time(my_air_conf["max_days"], to_time)

            ret = asyncio.run(my_air.get_samples(last_report_time, from_time, to_time, influxConnector.measurement))
            if ret:
                influxConnector.add_samples(ret[1])
                last_report_time = ret[0]

            time.sleep(sleep_time)

except FileNotFoundError as e:
    logging.error(f"Missing {file} file.")
    exit(2)

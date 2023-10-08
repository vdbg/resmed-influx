# MyAir Resmed to InfluxDB

Allows for importing [MyAir](https://myair.resmed.com/) data to [InfluxDB](https://www.influxdata.com/).

## Requirements

- The MyAir credentials associated with the [ResMed CPAP](https://www.resmed.com/en-us/sleep-apnea/cpap-products/cpap-machines/) that's uploading MyAir data to the cloud
- A device, capable of running either Docker containers or Python e.g., [Raspbian](https://www.raspbian.org/) or Windows
- [InfluxDB](https://en.wikipedia.org/wiki/InfluxDB) v2 installed and accessible from the device running the import
- Bucket created on the influxDB and token available

## Setup

Choose one of these 2 methods.

### Using Docker image built from source

1. `git clone https://github.com/vdbg/resmed-influx.git`
2. `cd resmed-influx`
3. edit the .env with your myAir Credientals
4. `docker compose up -d`
  * To see logs: `sudo docker container logs -f myAir`
  * If you change your credientials after the initial run they will need to be updated in config.toml as well

### Running directly on the device

[Python](https://www.python.org/) 3.11+ with pip3 required. `sudo apt-get install python3-pip` will install pip3 on ubuntu/raspbian systems if missing.

1. `git clone https://github.com/vdbg/resmed-influx.git`
2. `cd resmed-influx`
3. `cp template.config.toml config.toml`
4. Edit `config.toml` by following the instructions in the file
5. `pip3 install -r requirements.txt`
6. Run the program:
  * Interactive mode: `python3 main.py`
  * Shorter: `.\main.py` (Windows) or `./main.py` (any other OS).
  * As a background process (on non-Windows OS): `python3 main.py > log.txt 2>&1 &`
7. To exit: `Ctrl-C` if running in interactive mode, `kill` the process otherwise.

## Troubleshooting

The app may fail on first run, or may start failing after a long period of successful runs with a "policyNotAccepted" error.
If this happens, navigate to the [myAir web - ResMed](https://myair.resmed.com) site, enter your credentials, and accept myAir's policy.

## Grafana

[This template](grafana/dashboard.json) is what produced the following [Grafana](https://grafana.com/) dashboard:
![Grafana dashboard](grafana/dashboard.png)

Note: the dashboard uses influxdb v1 compatibility mode. [This page](https://www.techetio.com/2021/11/29/influxdb-v2-using-the-v1-api-for-v1-dependent-applications/) explains how to enable it.

## Credits

All the [myAir adapter code](myair_client/) was copied from [here](https://github.com/prestomation/resmed_myair_sensors/tree/master/custom_components/resmed_myair/client).

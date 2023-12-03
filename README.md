# MyAir Resmed to InfluxDB

Allows for importing [MyAir](https://myair.resmed.com/) data to [InfluxDB](https://www.influxdata.com/).

## Requirements

- The MyAir credentials associated with the [ResMed CPAP](https://www.resmed.com/en-us/sleep-apnea/cpap-products/cpap-machines/) that's uploading MyAir data to the cloud
- A device, capable of running either Docker containers or Python e.g., [Raspbian](https://www.raspbian.org/) or Windows
- [InfluxDB](https://en.wikipedia.org/wiki/InfluxDB) v2 installed and accessible from the device running the import
- Bucket created on the influxDB and token available

## Setup

The app reads the settings from `template.config.toml`, then `config.toml` (if it exists), then environment variables.
See `template.config.toml` for details.

Choose one of these methods.

### Using pre-built Docker image (recommended)

1. `touch config.toml`
2. This will fail due to malformed config.toml. That's intentional :)
   ``sudo docker run --name myAir -v "`pwd`/config.toml:/app/config.toml" vdbg/resmed-influx``
3. `sudo docker cp myAir:/app/template.config.toml config.toml`
4. Edit `config.toml` by following the instructions in the file
5. `sudo docker start myAir -i -e MYAIR_INFLUX_MAIN_LOG_VERBOSITY=DEBUG`
  This will display logging on the command window allowing for rapid troubleshooting. `Ctrl-C` to stop the container.
7. When done testing the config:
  * `sudo docker container rm myAir`
  * ``sudo docker run -d --name myAir -v "`pwd`/config.toml:/app/config.toml" --restart=always --memory=100m vdbg/resmed-influx``
  * To see logs: `sudo docker container logs -f myAir`

### Using Docker image built from source

1. `git clone https://github.com/vdbg/resmed-influx.git`
2. `sudo docker build -t resmed-influx-image resmed-influx/`
3. `cd resmed-influx`
4. `cp template.config.toml config.toml`
5. Edit `config.toml` by following the instructions in the file
6. Test run: ``sudo docker run --name myAir -v "`pwd`/config.toml:/app/config.toml" resmed-influx-image``
   This will display logging on the command window allowing for rapid troubleshooting. `Ctrl-C` to stop the container.
7. If container needs to be restarted for testing: `sudo docker start myAir -i`
8. When done testing the config:
  * `sudo docker container rm myAir`
  * ``sudo docker run -d --name myAir -v "`pwd`/config.toml:/app/config.toml" --restart=always --memory=100m resmed-influx-image``
  * To see logs: `sudo docker container logs -f myAir`


### With Docker without config file

Dependency: Docker installed.

Inspect `template.config.toml` file for all the settings that need to be overriden. Command will look something like:

```
sudo docker run \
  -d \
  --name myAir \
  --memory=100m \
  --pull=always \
  --restart=always \
  -e MYAIR_INFLUX_RESMED_LOGIN=user \
  -e MYAIR_INFLUX_RESMED_PASSWORD=password \
  -e MYAIR_INFLUX_INFLUX_TOKEN=token \
  vdbg/resmed-influx
```

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

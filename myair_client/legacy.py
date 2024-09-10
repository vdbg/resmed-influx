from typing import List, Any
import aiohttp
import datetime
import json
import re
import logging
from bs4 import BeautifulSoup
from .client import (
    MyAirDevice,
    MyAirClient,
    MyAirConfig,
    SleepRecord,
    AuthenticationError,
    TwoFactorNotSupportedError,
)

_LOGGER = logging.getLogger(__name__)

EU_CONFIG = {
    "authn_url": "https://myair.resmed.eu/authenticationids/externalwebservices/restotprequestselect.php",
    "dashboard_url": "https://myair.resmed.eu/Dashboard.aspx",
    "device_url": "https://myair.resmed.eu/myAccountDevice.aspx",
    "initiate_otp": "https://myair.resmed.eu/authenticationids/externalwebservices/restotpsend.php",
}

def generate_sleep_records(scores: Any) -> List[SleepRecord]:
    """Convert raw sleep score data into structured SleepRecord objects."""
    records: List[SleepRecord] = []

    def as_float(d, key):
        try:
            return float(d.get(key, 0))
        except (ValueError, TypeError):
            return 0

    current_year = datetime.datetime.now().year
    for score in scores:
        record: SleepRecord = {}
        try:
            month_num = datetime.datetime.strptime(score["MonthNameAbrv"], "%b").month
        except ValueError:
            _LOGGER.warning(f"Invalid month abbreviation: {score['MonthNameAbrv']}")
            continue

        # Handle potential future date by adjusting year
        start_date = datetime.datetime(
            current_year, month_num, int(score["DayNumber"])
        )
        if start_date > datetime.datetime.now():
            start_date = start_date.replace(year=current_year - 1)

        record["startDate"] = start_date.strftime("%Y-%m-%d")
        record["totalUsage"] = as_float(score, "Usage") * 60  # Convert hours to minutes
        record["sleepScore"] = as_float(score, "Score")
        record["usageScore"] = as_float(score, "UsageScore")
        record["ahiScore"] = as_float(score, "EventsScore")
        record["maskScore"] = as_float(score, "MaskScore")
        record["leakScore"] = as_float(score, "LeakScore")
        record["ahi"] = as_float(score, "Events")
        record["maskPairCount"] = as_float(score, "Mask")

        records.append(record)

    return records

class MyAirLegacyClient(MyAirClient):
    """Client to interact with the legacy myAir system for European users."""

    config: MyAirConfig
    client: aiohttp.ClientSession

    def __init__(self, config: MyAirConfig, client: aiohttp.ClientSession):
        assert config.region == "EU", "This client is only for EU regions"
        self.config = config
        self.client = client

    async def connect(self):
        """Authenticate the user and handle the login process."""
        _LOGGER.info("Attempting to authenticate with the legacy myAir system.")
        try:
            async with self.client.post(
                EU_CONFIG["authn_url"],
                json={
                    "authentifier": self.config.username,
                    "password": self.config.password,
                },
            ) as authn_res:
                authn_json = await authn_res.json()

                if not authn_json.get("sessionids"):
                    raise AuthenticationError("Invalid username or password")

                if isinstance(authn_json.get("modes"), list):
                    raise TwoFactorNotSupportedError(
                        "2-factor authentication is enabled, which is not supported by this integration."
                    )

        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error during authentication: {e}")
            raise AuthenticationError("Failed to authenticate with myAir.")

    async def get_user_device_data(self) -> MyAirDevice:
        """Fetch device data from the dashboard page."""
        _LOGGER.info("Fetching user device data from the myAir dashboard.")
        page = await self.get_dashboard_html()
        soup = BeautifulSoup(page, features="html.parser")

        equipment = soup.select("h6.c-equipment-label")
        if len(equipment) >= 2:
            manufacturer, device_name = equipment[1].renderContents().decode("utf8").split(" ", 1)
        else:
            _LOGGER.warning("Device information not found, using default values.")
            manufacturer = "ResMed"
            device_name = "Unknown"

        device: MyAirDevice = {
            "serialNumber": self.config.username,
            "deviceType": device_name,
            "lastSleepDataReportTime": "Unknown",
            "localizedName": f"{manufacturer} {device_name}",
            "fgDeviceManufacturerName": manufacturer,
            "fgDevicePatientId": "Unknown",
        }
        return device

    async def get_dashboard_html(self) -> str:
        """Retrieve the HTML content of the myAir dashboard page."""
        _LOGGER.info("Fetching dashboard HTML.")
        try:
            async with self.client.get(EU_CONFIG["dashboard_url"]) as dashboard_res:
                return await dashboard_res.text()
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Failed to retrieve dashboard HTML: {e}")
            raise

    async def get_sleep_records(self, from_time: datetime.datetime, to_time: datetime.datetime) -> List[SleepRecord]:
        """Fetch and parse sleep records from the dashboard page."""
        _LOGGER.info(f"Fetching sleep records from {from_time} to {to_time}.")
        page = await self.get_dashboard_html()
        soup = BeautifulSoup(page, features="html.parser")

        scripts = soup.find_all("script")
        scores_script = next(
            (x.renderContents().decode("utf8") for x in scripts if "myScores" in x.renderContents().decode("utf8")),
            None
        )

        if not scores_script:
            _LOGGER.error("Could not find the scores script in the dashboard page.")
            return []

        matches = re.search(r".+(\[.+?\]).+", scores_script)
        if not matches:
            _LOGGER.error("Could not extract scores from the dashboard script.")
            return []

        try:
            my_scores = json.loads(matches.groups()[0])
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Error parsing scores JSON: {e}")
            return []

        return generate_sleep_records(my_scores)

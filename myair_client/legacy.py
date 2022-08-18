# Copied from https://github.com/prestomation/resmed_myair_sensors/tree/master/custom_components/resmed_myair/client

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
    records: List[SleepRecord] = []

    def as_float(d, key):
        try:
            return float(d.get(key, 0))
        except ValueError:
            return 0

    for score in scores:
        record: SleepRecord = {}
        month_num = datetime.datetime.strptime(score["MonthNameAbrv"], "%b").month
        # This API doesn't give us a year, so we will guess!
        # If it's in the future, we assume it was from last year and subtract a year
        # Super-hacky but myAir does not give us a year
        year = datetime.datetime.now().year
        start_date = datetime.datetime.strptime(
            f"{year}-{month_num}-{score['DayNumber']}", "%Y-%M-%d"
        )
        record["startDate"] = start_date.strftime("%Y-%M-%d")

        # Usage is in hours, but we expose minutes
        record["totalUsage"] = as_float(score, "Usage") * 60
        record["sleepScore"] = as_float(score, "Score")
        record["usageScore"] = as_float(score, "UsageScore")
        record["ahiScore"] = as_float(score, "EventsScore")
        record["maskScore"] = as_float(score, "MaskScore")
        record["leakScore"] = as_float(score, "LeakScore")
        record["ahi"] = as_float(score, "Events")
        record["maskPairCount"] = as_float(score, "Mask")
        # record["leakPercentile"] = ?
        # record["sleepRecordPatienId"] =  ?

        records.append(record)

    # We are currently relying on myAir to return data sorted by date, e.g. the last record will be the latest record
    return records


class MyAirLegacyClient(MyAirClient):

    config: MyAirConfig
    client: aiohttp.ClientSession

    def __init__(self, config: MyAirConfig, client: aiohttp.ClientSession):
        assert config.region == "EU"
        self.config = config
        self.client = client

    async def connect(self):

        async with self.client.post(
            EU_CONFIG["authn_url"],
            json={
                "authentifier": self.config.username,
                "password": self.config.password,
            },
        ) as authn_res:
            authn_json = await authn_res.json()

            if authn_json["sessionids"] is None:
                raise AuthenticationError("Invalid username or password")

            if isinstance(authn_json["modes"], list):
                raise TwoFactorNotSupportedError(
                    "2-factor auth is enabled on your account. This is not supported by this integration. Tracking at https://github.com/prestomation/resmed_myair_sensors/issues/16"
                )

    async def get_user_device_data(self) -> MyAirDevice:
        page = await self.get_dashboard_html()
        soup = BeautifulSoup(page, features="html.parser")

        equipment = soup.select("h6.c-equipment-label")
        if len(equipment) >= 2:
            # Usually there are two labels fitting this selector, first is the mask
            # and second is the CPAP
            # So let's look at the second
            manufacturer, device_name = (
                equipment[1].renderContents().decode("utf8").split(" ", 1)
            )
        else:
            # But let's fallback to unknown incase this is not found
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

        async with self.client.get(EU_CONFIG["dashboard_url"]) as dashboard_res:
            page = await dashboard_res.text()
            return page

    async def get_sleep_records(self, from_time: datetime, to_time: datetime) -> List[SleepRecord]:
        page = await self.get_dashboard_html()
        soup = BeautifulSoup(page, features="html.parser")

        scripts = soup.find_all("script")
        scores_script = [
            x.renderContents().decode("utf8")
            for x in scripts
            if "myScores" in x.renderContents().decode("utf8")
        ][0]
        matches = re.search(".+(\[.+?\]).+", scores_script).groups()[0]
        my_scores = json.loads(matches)
        return generate_sleep_records(my_scores)

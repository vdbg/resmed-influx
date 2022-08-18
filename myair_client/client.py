# Copied from https://github.com/prestomation/resmed_myair_sensors/tree/master/custom_components/resmed_myair/client

import datetime
from typing import NamedTuple, TypedDict, List, Literal
from abc import ABC


class AuthenticationError(Exception):
    """This error is thrown when Authentication fails, which can mean the username/password or domain is incorrect"""

    pass


class TwoFactorNotSupportedError(Exception):
    """This error is thrown when 2-factor/OTP is enabled, this is not yet supported"""

    pass


class MyAirConfig(NamedTuple):
    """
    This is our config for logging into MyAir
    If you are in North America, you only need to set the username/password
    If you are in a different region, you will likely need to override these values.
    To do so, you will need to examine the network traffic during login to find the right values
    """

    username: str
    password: str
    region: Literal["NA", "EU"]


class SleepRecord(TypedDict):
    """
    This data is what is returned by the API and shown on the myAir dashboard
    No processing is performed
    """

    # myAir returns this in the format %Y-%m-%d, at daily precision
    startDate: str
    totalUsage: int
    sleepScore: int
    usageScore: int
    ahiScore: int
    maskScore: int
    leakScore: int
    ahi: float
    maskPairCount: int
    leakPercentile: float
    sleepRecordPatientId: str


class MyAirDevice(TypedDict):
    serialNumber: str
    deviceType: str
    lastSleepDataReportTime: str
    localizedName: str
    fgDeviceManufacturerName: str
    fgDevicePatientId: str

    # URI on the domain: https://static.myair-prd.dht.live/
    imagePath: str


class MyAirClient(ABC):
    async def connect(self):
        raise NotImplementedError()

    async def get_user_device_data(self) -> MyAirDevice:
        raise NotImplementedError()

    async def get_sleep_records(self, from_time: datetime, to_time: datetime) -> List[SleepRecord]:
        raise NotImplementedError()

import datetime
from typing import NamedTuple, TypedDict, List, Literal
from abc import ABC, abstractmethod


class AuthenticationError(Exception):
    """Raised when authentication fails due to incorrect username, password, or region settings."""
    pass


class TwoFactorNotSupportedError(Exception):
    """Raised when two-factor authentication (2FA) or OTP is enabled, which is not supported."""
    pass


class MyAirConfig(NamedTuple):
    """
    Configuration for logging into MyAir.

    Attributes:
        username (str): The username for MyAir.
        password (str): The password for MyAir.
        region (Literal["NA", "EU"]): The region in which the user is located, either North America (NA) or Europe (EU).
    """
    username: str
    password: str
    region: Literal["NA", "EU"]


class SleepRecord(TypedDict):
    """
    A dictionary representing a single sleep record, as returned by the MyAir API.

    Attributes:
        startDate (str): The date the sleep record starts (format: YYYY-MM-DD).
        totalUsage (int): The total usage time in minutes.
        sleepScore (int): The overall sleep score for the night.
        usageScore (int): The usage score for the device.
        ahiScore (int): The AHI (Apnea-Hypopnea Index) score.
        maskScore (int): The score for mask fit during the night.
        leakScore (int): The score for mask leaks during the night.
        ahi (float): The AHI value (apnea events per hour).
        maskPairCount (int): The number of times the mask was paired.
        leakPercentile (float): The percentile of leaks during the night.
        sleepRecordPatientId (str): The unique ID for the sleep record associated with the patient.
    """
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
    """
    A dictionary representing a MyAir device, typically a CPAP machine.

    Attributes:
        serialNumber (str): The serial number of the device.
        deviceType (str): The type of device.
        lastSleepDataReportTime (str): The last time the device reported sleep data.
        localizedName (str): The localized name of the device.
        fgDeviceManufacturerName (str): The manufacturer of the device.
        fgDevicePatientId (str): The ID of the patient using the device.
        imagePath (str): The path to the device image on the MyAir domain.
    """
    serialNumber: str
    deviceType: str
    lastSleepDataReportTime: str
    localizedName: str
    fgDeviceManufacturerName: str
    fgDevicePatientId: str
    imagePath: str


class MyAirClient(ABC):
    """
    Abstract base class for MyAir clients.

    This class defines the interface for connecting to MyAir, retrieving device data, and fetching sleep records. 
    Subclasses must implement the following methods:
        - `connect()`: Authenticate and establish a connection with the MyAir service.
        - `get_user_device_data()`: Fetch device information for the user.
        - `get_sleep_records()`: Retrieve sleep records for the specified date range.
    """

    @abstractmethod
    async def connect(self):
        """Authenticate with MyAir and establish a connection. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the 'connect' method.")

    @abstractmethod
    async def get_user_device_data(self) -> MyAirDevice:
        """Retrieve user device data from MyAir. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the 'get_user_device_data' method.")

    @abstractmethod
    async def get_sleep_records(self, from_time: datetime.datetime, to_time: datetime.datetime) -> List[SleepRecord]:
        """
        Retrieve sleep records from MyAir within the specified date range.

        Args:
            from_time (datetime.datetime): The start date for fetching records.
            to_time (datetime.datetime): The end date for fetching records.

        Returns:
            List[SleepRecord]: A list of sleep records between the specified dates.
        """
        raise NotImplementedError("Subclasses must implement the 'get_sleep_records' method.")

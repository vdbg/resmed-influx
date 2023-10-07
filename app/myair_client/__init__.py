from aiohttp import ClientSession
from .legacy import MyAirLegacyClient
from .rest import MyAirRESTClient
from .client import MyAirConfig


def get_client(config: MyAirConfig, session: ClientSession):
    if config.region == "NA":
        return MyAirRESTClient(config, session)
    if config.region == "EU":
        return MyAirLegacyClient(config, session)
    assert False, "Region must be NA or EU"

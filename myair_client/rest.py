from typing import NamedTuple, List, Any, Optional
import datetime
import json
import base64
import os
import re
import hashlib
import jwt
import logging
from urllib.parse import urldefrag, parse_qs
import aiohttp
from aiohttp import ClientSession
from .client import MyAirClient, MyAirConfig, MyAirDevice, SleepRecord, AuthenticationError

US_CONFIG = {
    "authn_client_id": "aus4ccsxvnidQgLmA297",
    "authorize_client_id": "0oa4ccq1v413ypROi297",
    "myair_api_key": "da2-cenztfjrezhwphdqtwtbpqvzui",
    "authn_url": "https://resmed-ext-1.okta.com/api/v1/authn",
    "authorize_url": "https://resmed-ext-1.okta.com/oauth2/{authn_client_id}/v1/authorize",
    "token_url": "https://resmed-ext-1.okta.com/oauth2/{authn_client_id}/v1/token",
    "appsync_url": "https://bs2diezuffgt5mfns4ucyz2vea.appsync-api.us-west-2.amazonaws.com/graphql",
    "oauth_redirect_url": "https://myair2.resmed.com",
}

class MyAirRESTClient(MyAirClient):
    """
    This client is used in North America for interacting with the myAir API.
    It handles OAuth authentication and GraphQL queries to fetch sleep data and device information.
    """

    config: MyAirConfig
    access_token: str
    id_token: str
    session: ClientSession

    def __init__(self, config: MyAirConfig, session: ClientSession):
        assert config.region == "NA", "REST client is only supported in North America (NA)."
        self.config = config
        self.session = session

    async def connect(self):
        """Authenticate and store the access token."""
        logging.info("Connecting to MyAir API and obtaining access token.")
        await self.get_access_token()

    async def get_access_token(self) -> str:
        """Obtain an access token using OAuth and PKCE (Proof Key for Code Exchange)."""
        try:
            # Step 1: Authenticate and obtain a session token
            logging.info("Authenticating with Okta to get session token.")
            session_token = await self._get_session_token()

            # Step 2: Obtain an OAuth authorization code using PKCE
            logging.info("Getting authorization code via PKCE.")
            authorization_code, code_verifier = await self._get_authorization_code(session_token)

            # Step 3: Exchange the authorization code for an access token
            logging.info("Exchanging authorization code for access token.")
            self.access_token, self.id_token = await self._exchange_token(authorization_code, code_verifier)
            return self.access_token

        except Exception as e:
            logging.exception(f"Error while obtaining access token: {e}")
            raise AuthenticationError("Failed to authenticate and retrieve access token.")

    async def _get_session_token(self) -> str:
        """Authenticate and obtain a session token from Okta."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        auth_payload = {"username": self.config.username, "password": self.config.password}

        async with self.session.post(US_CONFIG["authn_url"], headers=headers, json=auth_payload) as authn_res:
            authn_json = await authn_res.json()

        if "sessionToken" not in authn_json:
            logging.error("Authentication failed: No session token found.")
            raise AuthenticationError()

        return authn_json["sessionToken"]

    async def _get_authorization_code(self, session_token: str) -> (str, str):
        """Obtain an authorization code using the session token and PKCE."""
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        headers = {"Content-Type": "application/json"}
        authorize_url = US_CONFIG["authorize_url"].format(authn_client_id=US_CONFIG["authn_client_id"])
        params = {
            "client_id": US_CONFIG["authorize_client_id"],
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "none",
            "redirect_uri": US_CONFIG["oauth_redirect_url"],
            "response_mode": "fragment",
            "response_type": "code",
            "sessionToken": session_token,
            "scope": "openid profile email",
            "state": "abcdef",
        }

        async with self.session.get(authorize_url, headers=headers, params=params, allow_redirects=False) as res:
            location = res.headers.get("Location")
            if not location:
                logging.error("Failed to get authorization code. Location header missing.")
                raise AuthenticationError()

        fragment = urldefrag(location)
        code = parse_qs(fragment.fragment)["code"][0]
        return code, code_verifier

    async def _exchange_token(self, code: str, code_verifier: str) -> (str, str):
        """Exchange the authorization code for an access token."""
        token_payload = {
            "client_id": US_CONFIG["authorize_client_id"],
            "redirect_uri": US_CONFIG["oauth_redirect_url"],
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "code": code,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with self.session.post(US_CONFIG["token_url"].format(authn_client_id=US_CONFIG["authn_client_id"]),
                                     headers=headers, data=token_payload, allow_redirects=False) as token_res:
            token_data = await token_res.json()

        if "access_token" not in token_data or "id_token" not in token_data:
            logging.error("Failed to retrieve tokens from token response.")
            raise AuthenticationError()

        return token_data["access_token"], token_data["id_token"]

    def _generate_code_verifier(self) -> str:
        """Generate a code verifier for PKCE."""
        verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
        return re.sub(r"[^a-zA-Z0-9]+", "", verifier)

    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate a code challenge from a code verifier."""
        challenge = hashlib.sha256(verifier.encode("utf-8")).digest()
        challenge = base64.urlsafe_b64encode(challenge).decode("utf-8").replace("=", "")
        return challenge

    async def gql_query(self, operation_name: str, query: str) -> Any:
        """Perform a GraphQL query on the myAir AppSync API."""
        authz_header = f"bearer {self.access_token}"
        jwt_data = jwt.decode(self.id_token, options={"verify_signature": False})
        country_code = jwt_data.get("myAirCountryId")

        headers = {
            "x-api-key": US_CONFIG["myair_api_key"],
            "Authorization": authz_header,
            "rmdhandsetid": "02c1c662-c289-41fd-a9ae-196ff15b5166",
            "rmdlanguage": "en",
            "rmdhandsetmodel": "Chrome",
            "rmdhandsetosversion": "96.0.4664.110",
            "rmdproduct": "myAir",
            "rmdappversion": "1.0",
            "rmdhandsetplatform": "Web",
            "rmdcountry": country_code,
            "accept-language": "en-US,en;q=0.9",
        }

        logging.info(f"Performing GraphQL query: {operation_name}")
        async with self.session.post(US_CONFIG["appsync_url"], headers=headers, json={"operationName": operation_name, "query": query}) as res:
            return await res.json()

    async def get_sleep_records(self, from_time: datetime, to_time: datetime) -> List[SleepRecord]:
        """Fetch sleep records for a given date range."""
        start_month = from_time.strftime("%Y-%m-%d")
        end_month = to_time.strftime("%Y-%m-%d")

        query = f"""
        query GetPatientSleepRecords {{
            getPatientWrapper {{
                sleepRecords(startMonth: "{start_month}", endMonth: "{end_month}") {{
                    items {{
                        startDate
                        totalUsage
                        sleepScore
                        usageScore
                        ahiScore
                        maskScore
                        leakScore
                        ahi
                        maskPairCount
                        leakPercentile
                    }}
                }}
            }}
        }}
        """

        records_json = await self.gql_query("GetPatientSleepRecords", query)
        return records_json["data"]["getPatientWrapper"]["sleepRecords"]["items"]

    async def get_user_device_data(self) -> MyAirDevice:
        """Fetch user device data."""
        query = """
        query getPatientWrapper {
            getPatientWrapper {
                fgDevices {
                    serialNumber
                    deviceType
                    lastSleepDataReportTime
                    localizedName
                }
            }
        }
        """
        records_json = await self.gql_query("getPatientWrapper", query)
        return records_json["data"]["getPatientWrapper"]["fgDevices"][0]

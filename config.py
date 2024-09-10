import logging
import os
import tomllib
from pathlib import Path
from typing import Optional, Dict


class Config:
    """
    A class to handle loading configuration from TOML files and environment variables.

    Attributes:
        file (str): The name of the configuration file to load.
        prefix (str): The prefix used for overriding configurations via environment variables.
    """

    def __init__(self, file: str, prefix: str) -> None:
        """
        Initialize the Config object with the file name and prefix for environment variables.

        Args:
            file (str): The configuration file name to load (without the "template." prefix).
            prefix (str): The prefix to use for environment variable overrides.
        """
        self._file = file
        self._prefix = prefix

    def _load_file(self, file: str) -> Optional[Dict[str, Dict]]:
        """
        Load a TOML configuration file.

        Args:
            file (str): The name of the TOML file to load.

        Returns:
            Optional[Dict[str, Dict]]: The parsed configuration as a dictionary, or None if the file is not found.
        """
        try:
            with open(Path(__file__).with_name(file), "rb") as config_file:
                return tomllib.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f"Configuration file not found: {e.filename}.")
        except Exception as e:
            logging.error(f"Error loading configuration file {file}: {e}")
        return None

    def load(self) -> Dict[str, Dict]:
        """
        Load the configuration, merging values from a template file, an optional configuration file,
        and environment variables.

        Returns:
            Dict[str, Dict]: The final configuration after merging values from files and environment variables.

        Raises:
            Exception: If the template configuration file cannot be found.
        """
        # Load the template configuration file
        config = self._load_file(f"template.{self._file}")
        if not config:
            raise Exception(f"Template configuration file template.{self._file} is required and missing.")

        # Overwrite template with user configuration file if it exists
        user_config = self._load_file(self._file)
        if user_config:
            for section, settings in user_config.items():
                config[section].update(settings)

        # Overwrite with environment variables if they exist
        for section, settings in config.items():
            for key, value in settings.items():
                env_key = f"{self._prefix}_{section}_{key}".upper()
                config[section][key] = os.environ.get(env_key, value)

        return config

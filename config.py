import logging
import os
import tomllib
from pathlib import Path


class Config:
    def __init__(self, file: str, prefix: str) -> None:
        self._file = file
        self._prefix = prefix

    def __load__(self, file: str) -> dict[str, dict] | None:
        try:
            with open(Path(__file__).with_name(file), "rb") as config_file:
                return tomllib.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f"Missing {e.filename}.")
        return None

    def load(self) -> dict[str, dict]:
        ret = self.__load__("template." + self._file)
        if not ret:
            raise Exception(f"File template.{self._file} required.")

        # overwrite template with config, if exists
        config = self.__load__(self._file)
        if config:
            for k, v in config.items():
                for kk, vv in v.items():
                    ret[k][kk] = vv

        # overwrite with environment variables, if exist
        for k, v in ret.items():
            for kk, vv in v.items():
                key = f"{self._prefix}_{k}_{kk}".upper()
                ret[k][kk] = os.environ.get(key, vv)

        return ret

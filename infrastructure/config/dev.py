from dataclasses import dataclass

from base import BaseConfig


@dataclass(frozen=True)
class DevConfig(BaseConfig):
    ENV = "dev"

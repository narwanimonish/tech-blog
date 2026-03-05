from dataclasses import dataclass

from .base import BaseConfig


@dataclass(frozen=True)
class ProdConfig(BaseConfig):
    ENV = "prod"

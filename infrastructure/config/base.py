from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseConfig(ABC):
    ENV: str     

    APP_NAME: str = "tech-blog"
    
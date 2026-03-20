from dataclasses import dataclass


@dataclass(frozen=True)
class BaseConfig:

    APP_NAME: str = "tech-blog"
    ENV: str = "dev"

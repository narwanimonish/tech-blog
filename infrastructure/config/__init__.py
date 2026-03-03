import os

from .dev import DevConfig
from .prod import ProdConfig


def get_config():
    """
    The Singleton Getter. 
    It determines the environment once and returns the same object.
    """
    env = os.getenv("APP_ENV", "dev").lower()
    
    if env == "prod":
        return ProdConfig()
    return DevConfig()

# We instantiate it here so it's loaded once when the module is imported
env_config = get_config()
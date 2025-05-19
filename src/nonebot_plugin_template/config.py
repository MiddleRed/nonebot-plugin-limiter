from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    cooldown_enable_persistence: bool | None = False


plugin_config: Config = get_plugin_config(Config)
global_config = get_driver().config

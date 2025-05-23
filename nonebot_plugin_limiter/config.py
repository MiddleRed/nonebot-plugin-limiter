from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    cooldown_enable_persistence: bool | None = False
    cooldown_save_interval: int | None = 60


plugin_config: Config = get_plugin_config(Config)

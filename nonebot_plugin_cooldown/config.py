from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    pass
    # TODO: cooldown_enable_persistence: bool | None = False


plugin_config: Config = get_plugin_config(Config)

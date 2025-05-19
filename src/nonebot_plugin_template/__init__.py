from nonebot import logger, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_uninfo")
require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-cooldown",
    description="通用消息冷却限制器",
    usage="",
    type="library",
    homepage="https://github.com/MiddleRed/nonebot-plugin-cooldown",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_uninfo"),
    extra={"author": "MiddleRed <middlered@outlook.com>"},
)

from arclet.alconna import Alconna, Args, Arparma, Option, Subcommand
from nonebot_plugin_alconna import on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage



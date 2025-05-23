from collections import deque
from datetime import datetime
import json
from pathlib import Path

from nonebot import get_driver
from nonebot.adapters import Bot
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler
import nonebot_plugin_localstore as store
from pydantic import BaseModel, ValidationError

from .config import plugin_config
from .cooldown import FixWindowUsage, SlidingWindowUsage, _FixWindowCooldownDict, _SlidingWindowCooldownDict, _tz

driver = get_driver()
plugin_data_file: Path = store.get_plugin_data_file("limiter_data.json")


class PersistData(BaseModel):
    class FixWindowSet(BaseModel):
        start_time: int
        available: int

    fix_window: dict[str, dict[str, FixWindowSet]] | None = None

    class SlidingWindowSet(BaseModel):
        timestamps: list[int]

    sliding_window: dict[str, dict[str, SlidingWindowSet]] | None = None


def load_usage_data() -> None:
    """加载本地存储的用量数据"""

    if not plugin_data_file.exists():
        return
    try:
        data = PersistData.model_validate_json(plugin_data_file.read_text())
    except ValidationError:
        logger.warning("Failed to load previous usage data (ValidationError), will ignore it.")
        return

    if data.fix_window is not None:
        for name, usage_set in data.fix_window.items():
            if name not in _FixWindowCooldownDict:
                _FixWindowCooldownDict[name] = {}
            bucket = _FixWindowCooldownDict[name]
            for _id, usage in usage_set.items():
                bucket[_id] = FixWindowUsage(
                    start_time=datetime.fromtimestamp(usage.start_time, tz=_tz),
                    available=usage.available,
                )

    if data.sliding_window is not None:
        for name, usage_set in data.sliding_window.items():
            if name not in _SlidingWindowCooldownDict:
                _SlidingWindowCooldownDict[name] = {}
            bucket = _SlidingWindowCooldownDict[name]
            for _id, usage in usage_set.items():
                bucket[_id] = SlidingWindowUsage(
                    timestamps=deque(datetime.fromtimestamp(t, tz=_tz) for t in usage.timestamps)
                )

    logger.info("Loaded previous usage data.")


def save_usage_data() -> None:
    """保存用量数据到本地"""

    j = {"fix_window": {}, "sliding_window": {}}

    for name, usage_set in _FixWindowCooldownDict.items():
        j["fix_window"][name] = {
            _id: {
                "start_time": int(usage.start_time.timestamp()),
                "available": usage.available,
            }
            for _id, usage in usage_set.items()
        }

    for name, usage_set in _SlidingWindowCooldownDict.items():
        j["sliding_window"][name] = {
            _id: {
                "timestamps": [int(t.timestamp()) for t in usage.timestamps],
            }
            for _id, usage in usage_set.items()
        }

    plugin_data_file.write_text(json.dumps(j))

@driver.on_startup
def _startup() -> None:
    if not plugin_config.cooldown_enable_persistence:
        return

    load_usage_data()
    scheduler.add_job(save_usage_data, "interval", seconds=plugin_config.cooldown_save_interval)
    if not scheduler.running:
        scheduler.start()


@driver.on_bot_disconnect
def _disconnect_save(bot: Bot) -> None:
    if not plugin_config.cooldown_enable_persistence:
        return

    save_usage_data()


@driver.on_shutdown
def _shutdown_save() -> None:
    if not plugin_config.cooldown_enable_persistence:
        return

    save_usage_data()

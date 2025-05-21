from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from nonebot.adapters import Bot, Event, Message, MessageSegment, MessageTemplate
from nonebot.internal.rule import Rule as Rule
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.typing import _DependentCallable
from nonebot_plugin_alconna import UniMessage
from tzlocal import get_localzone

from .entity import CooldownEntity


@dataclass
class FixWindowUsage:
    start_time: datetime
    available: int


_FixWindowCooldownDict: dict[str, dict[str, FixWindowUsage]] = {}


def Cooldown(
    entity: CooldownEntity | _DependentCallable[str],
    period: int | timedelta | str,
    *,
    limit: int | _DependentCallable[int] = 1,
    reject: None | str | Message | MessageSegment | MessageTemplate | UniMessage = None,
    name: None | str = None,
):
    """
    **固定窗口速率限制**

    用于限制指定对象在固定时间周期内的消息触发次数。

    参数:
        entity (CooldownEntity | _DependentCallable[str]):
            设置需要进行速率限制的对象。
            - 可传入 `CooldownEntity` 对象，如 `UserScope`, `GroupScope` 等。
            - 可传入返回值为 `str` 的函数，自定义限制对象的**唯一 ID**，支持依赖注入。

        period (int | datetime.timedelta | str):
            设置速率限制的重置时间。
            - 若为 `int` 或 `datetime.timedelta`，表示周期开始后经过指定时间后重置限制。
            - 若为 `str`，应为合法的 cron 表达式，表示按计划任务方式重置限制。

        limit (int | _DependentCallable[int]):
            可选，设置在每个周期内允许的最大触发次数。默认为 1。
            - 可传入返回值为 `int` 的函数，自定义最大触发次数，支持依赖注入。

        reject (None | str | Message | MessageSegment | MessageTemplate | UniMessage):
            可选，当超出限制时的响应行为。默认为 `None`。
            - 若为 `str` 或消息对象，将作为限制使用时的提示消息发送给用户。

        name (None | str):
            可选，设置当前限制器的使用统计集合。默认为 `None` ，即私有集合。
            - 当传入 `str` ，将创建或加入一个公共集合，可用于与其他命令的限制器共享使用统计。

    示例:
    ```python
    from nonebot.permission import SUPERUSER
    from nonebot_plugin_limiter.entity import UserScope

    @matcher.handle(parameterless=[
        Cooldown(
            UserScope(permission=SUPERUSER),
            5,
            limit = 2,
            reject="操作过于频繁，请稍后再试。"
        )
    ])
    async def handler(...): ...
    ```
    """

    if isinstance(entity, CooldownEntity):
        entity_id_dep = entity.get_entity_id
    else:
        entity_id_dep = entity

    if isinstance(period, str):
        trigger = CronTrigger.from_crontab(period)
    else:
        if isinstance(period, timedelta):
            interval_length = int(period.total_seconds())
        else:
            interval_length = period
        trigger = IntervalTrigger(seconds=interval_length)
    trigger = cast(BaseTrigger, trigger)

    if isinstance(limit, int):
        limit_dep = lambda: limit  # noqa: E731
    else:
        limit_dep = limit

    if isinstance(name, str):
        if name not in _FixWindowCooldownDict.keys():
            _FixWindowCooldownDict[name] = {}
        cooldown_dict = _FixWindowCooldownDict[name]
    else:
        cooldown_dict: dict[str, FixWindowUsage] = {}

    async def _limiter_dependency(
        bot: Bot,
        matcher: Matcher,
        event: Event,
        entity_id: str = Depends(entity_id_dep),
        limit: int = Depends(limit_dep),
    ) -> None:
        if entity_id == "__bypass":
            return

        now = datetime.now(tz=get_localzone())
        cooldown_dict.setdefault(entity_id, FixWindowUsage(now, limit))
        usage = cooldown_dict[entity_id]

        if usage.available > 0:
            usage.available -= 1
            return

        reset_time = trigger.get_next_fire_time(usage.start_time, now)

        assert reset_time is not None, "reset_time should not be None"
        if now >= reset_time:
            usage.start_time = now
            usage.available = limit - 1
            return

        if isinstance(reject, UniMessage):
            await reject.finish(event, bot)
        else:
            await matcher.finish(reject)

    return Depends(_limiter_dependency)

from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial
import inspect
from typing import Any, cast

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from nonebot.adapters import Bot, Event, Message, MessageSegment, MessageTemplate
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.rule import Rule as Rule
from nonebot.typing import T_State, _DependentCallable
from nonebot.utils import is_coroutine_callable, run_sync
from nonebot_plugin_alconna import UniMessage
from tzlocal import get_localzone

from .entity import BYPASS_ENTITY, CooldownEntity

_tz = get_localzone()
SupportMsgType = str | Message | MessageSegment | MessageTemplate | UniMessage


def _entity_id_dep_wrapper(entity: CooldownEntity | _DependentCallable[str]) -> _DependentCallable[str]:
    if isinstance(entity, CooldownEntity):
        entity_id_dep = entity.get_entity_id
    else:
        entity_id_dep = entity
    return entity_id_dep

def _limit_dep_wrapper(limit: int | _DependentCallable[int]) -> _DependentCallable[int]:
    if isinstance(limit, int):
        limit_dep = lambda: limit  # noqa: E731
    else:
        limit_dep = limit
    return limit_dep

def _reject_dep_wrapper(reject: None | SupportMsgType | _DependentCallable[Any]) -> _DependentCallable[Any]:
    if isinstance(reject, SupportMsgType):
        async def _send_msg(bot: Bot, matcher: Matcher, event: Event):
            if isinstance(reject, UniMessage):
                await reject.finish(event, bot)
            else:
                await matcher.finish(reject)
        reject_func = _send_msg
    elif reject is not None:    # callable
        if not is_coroutine_callable(reject):
            reject = run_sync(reject)
        reject_func = reject
    else:
        async def _null():
            return None
        reject_func = _null

    async def _inject_wrapper(*args, **kwargs):
        sig = inspect.signature(reject_func)
        bound = sig.bind(*args, **kwargs)
        return partial(reject_func, **bound.arguments)

    setattr(_inject_wrapper, "__signature__", inspect.signature(reject_func))
    #_inject_wrapper.__signature__ = inspect.signature(reject_func)
    return _inject_wrapper

def inject_increaser(state: T_State, func: Callable):
    executors = state.setdefault("plugin_limiter:increaser", [])
    assert isinstance(executors, list)
    executors.append(func)

# region: FixWindow
@dataclass
class FixWindowUsage:
    start_time: datetime
    available: int


_FixWindowCooldownDict: dict[str, dict[str, FixWindowUsage]] = {}


def Cooldown(
    entity: CooldownEntity | _DependentCallable[str],
    period: int | timedelta | str,
    *,
    limit: int | _DependentCallable[int] = 5,
    reject: None | SupportMsgType | _DependentCallable[Any] = None,
    set_increaser: bool = False,
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
            可选，设置在每个周期内允许的最大触发次数。默认为 5。
            - 可传入返回值为 `int` 的函数，自定义最大触发次数，支持依赖注入。

        reject (None | SupportMsgType | _DependentCallable):
            可选，当超出限制时的响应行为。默认为 `None`。
            - 若为 `str` 或消息对象，将作为限制使用时的提示消息发送给用户。
            - 若为依赖注入函数，将会在拒绝时进行调用。

        set_increaser (bool):
            可选，是否获取限制器的增加器。默认为 False。
            - 当启用该选项时，限制器默认的自增将会关闭，需要在事件处理时依赖获取 Increaser 并手动操作增加。

        name (None | str):
            可选，设置当前限制器的使用统计集合。默认为 `None` ，即私有集合。
            - 当传入 `str` ，将创建或加入一个同名公共集合，可用于与其他命令的限制器共享使用统计。

    示例:
    ```python
    from nonebot.permission import SUPERUSER
    from nonebot_plugin_limiter.entity import UserScope

    # 在 5 秒内最多触发 2 次
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

    if isinstance(period, str):
        trigger = CronTrigger.from_crontab(period)
    else:
        if isinstance(period, timedelta):
            interval_length = int(period.total_seconds())
        else:
            interval_length = period
        trigger = IntervalTrigger(seconds=interval_length)
    trigger = cast(BaseTrigger, trigger)

    if isinstance(name, str):
        if name not in _FixWindowCooldownDict.keys():
            _FixWindowCooldownDict[name] = {}
        bucket = _FixWindowCooldownDict[name]
    else:
        bucket: dict[str, FixWindowUsage] = {}

    async def _limiter_dependency(
        bot: Bot,
        matcher: Matcher,
        event: Event,
        state: T_State,
        entity_id: str = Depends(_entity_id_dep_wrapper(entity)),
        limit: int = Depends(_limit_dep_wrapper(limit)),
        reject_cb: Callable[..., Awaitable[Any]] = Depends(_reject_dep_wrapper(reject))
    ) -> None:
        if entity_id == BYPASS_ENTITY:
            return

        now = datetime.now(tz=_tz)

        if entity_id not in bucket:
            bucket[entity_id] = FixWindowUsage(now, limit)
        usage = bucket[entity_id]

        def _increase_action(reset: bool = True):
            if reset:
                usage.start_time = now
                usage.available = limit
            usage.available -= 1

        if usage.available > 0:
            if set_increaser:
                inject_increaser(state, partial(_increase_action, False))
            else:
                _increase_action(False)
            return

        # Calculate reset time based on when the limitation was set
        reset_time = trigger.get_next_fire_time(usage.start_time, now)
        assert reset_time is not None, "reset_time should not be None"

        # Reset
        if now >= reset_time:
            if set_increaser:
                inject_increaser(state, _increase_action)
            else:
                _increase_action()
            return  # Didn't exceed

        # Exceeded
        await reject_cb()
        raise FinishedException()

    return Depends(_limiter_dependency)

# endregin

# region: SlidingWindow
@dataclass
class SlidingWindowUsage:
    timestamps: deque[datetime] = field(default_factory=deque)


_SlidingWindowCooldownDict: dict[str, dict[str, SlidingWindowUsage]] = {}


def SlidingWindowCooldown(
    entity: CooldownEntity | _DependentCallable[str],
    period: int | timedelta,
    *,
    limit: int | _DependentCallable[int] = 5,
    reject: None | SupportMsgType | _DependentCallable[Any] = None,
    set_increaser: bool = False,
    name: None | str = None,
):
    """
    **滑动窗口速率限制**

    用于限制指定对象在任意长度为设定周期的时间窗口内的消息触发次数。

    参数:
        entity (CooldownEntity | _DependentCallable[str]):
            设置需要进行速率限制的对象。
            - 可传入 `CooldownEntity` 对象，如 `UserScope`, `GroupScope` 等。
            - 可传入返回值为 `str` 的函数，自定义限制对象的**唯一 ID**，支持依赖注入。

        period (int | datetime.timedelta):
            设置滑动窗口的时间长度。

        limit (int | _DependentCallable[int]):
            可选，设置在每个滑动窗口周期内允许的最大触发次数。默认为 5。
            - 可传入返回值为 `int` 的函数，自定义最大触发次数，支持依赖注入。

        reject (None | SupportMsgType):
            可选，当超出限制时的响应行为。默认为 `None`。
            - 若为 `str` 或消息对象，将作为限制使用时的提示消息发送给用户。
            - 若为依赖注入函数，将会在拒绝时进行调用。

        set_increaser (bool):
            可选，是否获取限制器的增加器。默认为 False。
            - 当启用该选项时，限制器默认的自增将会关闭，需要在事件处理时依赖获取 Increaser 并手动操作增加。

        name (None | str):
            可选，设置当前限制器的使用统计集合。默认为 `None` ，即私有集合。
            - 当传入 `str` ，将创建或加入一个同名公共集合，可用于与其他命令的限制器共享使用统计。

    示例:
    ```python
    from nonebot.permission import SUPERUSER
    from nonebot_plugin_limiter.entity import UserScope

    # 任意一分钟内最多触发 5 次
    @matcher.handle(parameterless=[
        SlidingWindowCooldown(
            UserScope(permission=SUPERUSER),
            60,
            limit=5,
            reject="请求过于频繁，请稍后再试。"
        )
    ])
    async def handler(...): ...
    ```
    """

    if isinstance(period, timedelta):
        window_length = int(period.total_seconds())
    else:
        window_length = int(period)

    if isinstance(name, str):
        bucket = _SlidingWindowCooldownDict.setdefault(name, {})
    else:
        bucket: dict[str, SlidingWindowUsage] = {}

    async def _limiter_dependency(
        bot: Bot,
        matcher: Matcher,
        event: Event,
        state: T_State,
        entity_id: str = Depends(_entity_id_dep_wrapper(entity)),
        limit: int = Depends(_limit_dep_wrapper(limit)),
        reject_cb: Callable[..., Awaitable[Any]] = Depends(_reject_dep_wrapper(reject))
    ) -> None:
        if entity_id == BYPASS_ENTITY:
            return

        now = datetime.now(tz=_tz)

        if entity_id not in bucket:
            bucket[entity_id] = SlidingWindowUsage()
        usage = bucket[entity_id]

        # Drop old timestamps
        while usage.timestamps and (now - usage.timestamps[0]).total_seconds() >= window_length:
            usage.timestamps.popleft()

        def _increase_action():
            usage.timestamps.append(now)

        if len(usage.timestamps) < limit:
            if set_increaser:
                inject_increaser(state, _increase_action)
            else:
                _increase_action()
            return  # Didn't exceed

        # Exceeded
        await reject_cb()
        raise FinishedException()

    return Depends(_limiter_dependency)

# endregin

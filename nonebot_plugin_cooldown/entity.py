from typing import Literal

from nonebot.permission import Permission
from nonebot.internal.adapter import Bot, Event

from nonebot_plugin_uninfo import get_session

_IdType = str | int


class CooldownEntity:
    """
    **限制实体基类**
    """

    __slots__ = ()

    def __init__(self) -> None: ...

    async def get_entity_id(self, bot: Bot, event: Event) -> str:
        """
        返回被限制实体的唯一标识符，统一为 str
        """
        ...


class GlobalScope(CooldownEntity):
    """
    **全局限制实体**

    限制所有用户在所有场景下的使用情况。
    """

    async def get_entity_id(self, bot: Bot, event: Event) -> str:
        return "__global"


class UserScope(CooldownEntity):
    """
    **用户限制实体**

    限制单个用户在所有场景下的使用情况。

    注意：不同平台的用户 ID 在不同场景可能不同，使用时请注意实际平台实现。
    """

    def __init__(self, *, whitelist: None | tuple[_IdType, ...], permission: Permission | None) -> None:
        """
        可选参数:
            whitelist (tuple[str | int]):
                白名单用户 ID 列表，在此名单内的将不受不受限制。
            permission: (Permission):
                NoneBot 权限，通过该权限检查的将不受限制。

        注：whitelist 与 permission 不互斥，通过任意一个条件即不受限制
        """
        
        self.whitelist = whitelist
        self.permission = permission

    async def get_entity_id(self, bot: Bot, event: Event) -> str:
        sess = await get_session(bot, event)
        if sess is None:
            return "__bypass"

        user_id = sess.user.id
        if self.whitelist is not None and user_id in self.whitelist:
            return "__bypass"
        if self.permission is not None and (await self.permission(bot, event)):
            return "__bypass"
        return f"u`{user_id}`"


class SceneScope(CooldownEntity):
    """
    **场景限制实体**

    限制非私聊场景下在该场景内的所有用户使用情况。
    """

    def __init__(self, *, whitelist: None | tuple[_IdType, ...], permission: Permission | None) -> None:
        """
        可选参数:
            whitelist (tuple[str | int]):
                白名单场景 ID 列表，在此名单内的将不受不受限制。
            permission: (Permission):
                NoneBot 权限，通过该权限检查的将不受限制。

        注：whitelist 与 permission 不互斥，通过任意一个条件即不受限制
        """

        self.whitelist = whitelist
        self.permission = permission

    async def get_entity_id(self, bot: Bot, event: Event) -> str:
        sess = await get_session(bot, event)
        if sess is None:
            return "__bypass"

        scene_id = sess.scene.id
        if self.whitelist is not None and scene_id in self.whitelist:
            return "__bypass"
        if self.permission is not None and (await self.permission(bot, event)):
            return "__bypass"
        return f"s`{scene_id}`"


class UserSceneScope(CooldownEntity):
    """
    **用户场景限制实体**

    限制单个用户在不同场景下的使用情况，各个场景使用情况相互独立。
    """

    def __init__(
        self,
        *,
        whitelist: None | tuple[tuple[_IdType | Literal["*"], _IdType | Literal["*"]], ...],
        permission: Permission | None,
    ) -> None:
        """
        可选参数:
            whitelist (tuple[tuple[str | int, str | int]]):
                白名单用户 ID 与场景 ID 组合列表，在此名单内的将不受不受限制。
            permission: (Permission):
                NoneBot 权限，通过该权限检查的将不受限制。

        注意：
            - 白名单中用户 ID 与场景 ID 组合为二元组，用户 ID 在前场景 ID 在后。
            - 用户 ID 和场景 ID 均可为 `*`，表示任意用户或任意场景。
            - whitelist 与 permission 不互斥，通过任意一个条件即不受限制。
        """

        self.whitelist = whitelist
        self.permission = permission

    async def get_entity_id(self, bot: Bot, event: Event) -> str:
        sess = await get_session(bot, event)
        if sess is None:
            return "__bypass"

        user_id = sess.user.id
        scene_id = sess.scene.id
        if self.whitelist is not None:
            for uid, sid in self.whitelist:
                if (uid == "*" or uid == user_id) and (sid == "*" or sid == scene_id):
                    return "__bypass"
        if self.permission is not None and (await self.permission(bot, event)):
            return "__bypass"
        return f"u`{user_id}`_s`{scene_id}`"

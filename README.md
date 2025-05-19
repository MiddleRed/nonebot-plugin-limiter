# nonebot-plugin-cooldown

提供一个简单易用的冷却（Cooldown）装饰器用于消息速率限制

## 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-cooldown --upgrade
使用 **pypi** 源安装

    nb plugin install nonebot-plugin-cooldown --upgrade -i "https://pypi.org/simple"
使用**清华源**安装

    nb plugin install nonebot-plugin-cooldown --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot-plugin-cooldown
安装仓库 master 分支

    uv add git+https://github.com/MiddleRed/nonebot-plugin-cooldown@master
</details>

<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-cooldown
安装仓库 master 分支

    pdm add git+https://github.com/{owner}/nonebot-plugin-cooldown@master
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-cooldown
安装仓库 master 分支

    poetry add git+https://github.com/{owner}/nonebot-plugin-cooldown@master
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_template"]

</details>

## 使用
*TBA*

## 配置
可启用消息速率状态持久化，防止机器人重启丢失先前的用户速率数据
```
# .env
COOLDOWN_ENABLE_PERSISTENCE = false
```

本插件的状态持久化使用 `nonebot_plugin_localstore` 存储于本地，如需更改缓存位置请参考[插件文档](https://github.com/nonebot/plugin-localstore?tab=readme-ov-file#%E9%85%8D%E7%BD%AE%E9%A1%B9)

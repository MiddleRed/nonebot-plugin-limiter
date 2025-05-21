# nonebot-plugin-limiter

提供一个简单易用的冷却（Cooldown）和限流依赖用于命令消息速率限制，支持跨平台。

## 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-limiter --upgrade
使用 **pypi** 源安装

    nb plugin install nonebot-plugin-limiter --upgrade -i "https://pypi.org/simple"
使用**清华源**安装

    nb plugin install nonebot-plugin-limiter --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot-plugin-limiter
安装仓库 master 分支

    uv add git+https://github.com/MiddleRed/nonebot-plugin-limiter@master
</details>

<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-limiter
安装仓库 master 分支

    pdm add git+https://github.com/{owner}/nonebot-plugin-limiter@master
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-limiter
安装仓库 master 分支

    poetry add git+https://github.com/{owner}/nonebot-plugin-limiter@master
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot-plugin-limiter"]

</details>

## 使用
*TBA*

### Feature
- [x] 固定窗口
- [x] 滑动窗口
- [ ] 漏桶
- [ ] 令牌桶
- [ ] reject handler 依赖注入
- [ ] 本地持久化状态

## 鸣谢
本插件部分代码参考了 [nonebot/adapter-onebot](https://github.com/nonebot/adapter-onebot) 的 `Cooldown` [实现](https://github.com/nonebot/adapter-onebot/blob/51294404cc8bf0b3d03008e09f34d3dd1a6acfd8/nonebot/adapters/onebot/v11/helpers.py#L224) ，在此表示感谢

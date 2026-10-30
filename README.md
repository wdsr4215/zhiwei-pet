# 知微桌宠
一只 Windows 桌面伙伴：离线记事、提醒、番茄钟、自由陪伴与可选 AI 问答。

## 下载
打开本仓库 Releases，下载 Zhiwei-Windows-x64.zip，解压整个文件夹到固定目录，运行 Zhiwei.exe。不要只移动exe；不要在压缩包内直接运行。当前版本未签名。
首次启动默认开启当前用户的开机启动，并显示说明；在工作台“设置与连接”随时关闭。删除程序前先关闭开机启动；移动目录后关闭再开启以更新路径。

## 隐私
记事和设置保存在 %LOCALAPPDATA%/ZhiweiPet，API密钥存入Windows凭据管理器，发布包不包含任何作者个人数据。对话仅驻留内存；用户主动问答或开启账户监测后才发送相关请求。无遥测，无自动上传笔记，无远程执行工具。
可选DeepSeek/OpenAI兼容接口由用户填写自己的密钥；ChatGPT订阅不等于API额度。Codex额度查询需用户本机安装并登录官方客户端；不扫描令牌文件。

## 开发
Python 3.12，运行 `pip install -r requirements.txt`，然后 `python main.py`。
测试：`python -m unittest discover -s tests -v`。
Windows打包：安装 `pyinstaller` 后运行 `build.ps1`。保留整个文件夹以及依赖许可，PySide6采用动态库分发。

## 参与
欢迎Fork、修改、分发和提交Pull Request；问题反馈请提Issue。代码使用MIT许可，允许商用；素材另见ASSETS-LICENSE.md，第三方权利不在许可范围内。
没有匿名主分支写入权限；任何人均可通过Fork/PR贡献，维护者审核后合并。

## 说明
非官方同人项目。动作使用透明帧图和程序动画，不是Live2D或3D骨骼。提醒依赖程序运行，退出或关机期间无法实时提醒，重启后补报。原始参考项目为 https://github.com/1190fasheqi/dafeiyu-pet ，MIT许可保留于licenses。

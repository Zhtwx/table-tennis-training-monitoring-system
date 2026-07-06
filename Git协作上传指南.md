# Git 协作上传指南

本文档用于把《乒乓球运动员综合训练监控管理系统》上传到 Git 远程仓库，并建立多人协作分支。

## 1. 当前状态说明

当前项目目录中原本有一个空的 `.git` 文件夹，但它不是有效 Git 仓库。需要重新执行：

```bash
git init -b main
```

由于当前工具环境对 `.git` 目录写入受限，无法由 Codex 直接完成初始化和推送。请在你自己的终端中执行下面步骤。

## 2. 上传前确认

请确认项目根目录中存在这些文件：

```text
app.py
run_server.bat
requirements.txt
.gitignore
.env.example
templates/
前端模板开发指导.md
项目部署指导手册.md
Git协作上传指南.md
```

不要提交以下目录：

```text
.venv/
__pycache__/
.agents/
.codex_tmp/
.env
```

这些内容已经写入 `.gitignore`。

## 3. 获取远程仓库地址

你需要先在 Git 平台创建一个空仓库，例如：

```text
GitHub
Gitee
GitLab
微信 Git
学校 Git 平台
```

创建完成后复制远程仓库地址，格式类似：

```text
https://github.com/用户名/仓库名.git
```

或：

```text
git@git.weixin.qq.com:xxx/xxx.git
```

## 4. 推荐分支规划

建议使用：

| 分支 | 用途 |
|---|---|
| `main` | 稳定展示版本，只放可运行代码 |
| `develop` | 日常集成分支，成员功能完成后先合并到这里 |
| `feature/auth-permission` | 登录、管理员、普通用户、权限控制 |
| `feature/player-query` | 运动员档案、多条件模糊组合查询 |
| `feature/training-import` | 专项技术录入、Excel 批量导入 |
| `feature/dashboard-echarts` | 统计看板、ECharts 图表 |
| `feature/injury-rehab` | 伤病记录、康复跟踪 |
| `feature/fitness-test` | 体能测试模块 |
| `feature/match-report` | 比赛成绩与报告模块 |
| `feature/system-settings` | 系统配置、数据字典 |
| `docs/deployment-guide` | 部署文档和协作说明 |

## 5. 一键脚本方式

项目根目录已经生成：

```text
setup_git_collaboration.bat
```

使用方法：

1. 右键编辑 `setup_git_collaboration.bat`
2. 找到这一行：

```bat
set "REMOTE_URL=请替换成你的远程仓库地址"
```

3. 替换为你的真实远程仓库地址，例如：

```bat
set "REMOTE_URL=https://gitee.com/your-name/table-tennis-training.git"
```

4. 保存后双击运行。

脚本会自动完成：

- 初始化 Git 仓库
- 设置主分支为 `main`
- 添加远程仓库 `origin`
- 提交当前代码
- 推送 `main`
- 创建 `develop`
- 创建多人协作功能分支
- 推送所有分支到远程仓库

## 6. 手动命令方式

如果不使用脚本，可以在项目根目录打开终端，依次执行：

```bash
git init -b main
git add .
git commit -m "Initial commit: table tennis training monitoring system"
git remote add origin 你的远程仓库地址
git push -u origin main
```

创建 `develop` 分支：

```bash
git checkout -b develop
git push -u origin develop
```

创建功能分支：

```bash
git checkout -b feature/auth-permission develop
git push -u origin feature/auth-permission

git checkout -b feature/player-query develop
git push -u origin feature/player-query

git checkout -b feature/training-import develop
git push -u origin feature/training-import

git checkout -b feature/dashboard-echarts develop
git push -u origin feature/dashboard-echarts

git checkout -b feature/injury-rehab develop
git push -u origin feature/injury-rehab

git checkout -b feature/fitness-test develop
git push -u origin feature/fitness-test

git checkout -b feature/match-report develop
git push -u origin feature/match-report

git checkout -b feature/system-settings develop
git push -u origin feature/system-settings

git checkout -b docs/deployment-guide develop
git push -u origin docs/deployment-guide
```

最后切回开发分支：

```bash
git checkout develop
```

## 7. 每位成员日常开发流程

第一次拉取：

```bash
git clone 远程仓库地址
cd 仓库名
```

切换自己的分支：

```bash
git checkout feature/player-query
```

每天开始写代码前：

```bash
git pull
```

提交代码：

```bash
git add .
git commit -m "说明本次修改内容"
git push
```

功能完成后：

```text
提交 Pull Request / Merge Request
请求合并到 develop
```

## 8. 注意事项

- 不要直接在 `main` 分支开发。
- 不要提交 `.venv`。
- 不要提交 `.env`。
- 不要提交数据库文件。
- 每个人只在自己的功能分支上开发。
- 合并到 `develop` 前先确认项目能启动。
- 最终答辩展示前，再由组长把 `develop` 合并到 `main`。

@echo off
chcp 65001 > nul
echo ================================
echo  AI 多模态助手 - Git 推送脚本
echo ================================
echo.

cd /d "%~dp0"

:: 检查 git
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未安装 Git！请先安装：https://git-scm.com/
    paus
    exit /b 1
)

:: 配置用户信息（首次运行会提示）
git config user.name >nul 2>&1 || (
    set /p name="请输入你的 GitHub 用户名: "
    git config user.name "![name]!"
)

git config user.email >nul 2>&1 || (
    set /p email="请输入你的 GitHub 邮箱: "
    git config user.email "![email]!"
)

:: 拉取远程最新代码
echo [1/4] 拉取远程最新代码...
git pul origin master --allow-unrelated-histories >nul 2>&1

:: 添加所有文件（.gitignore 会自动排除 .env、logs 等）
echo [2/4] 添加文件到暂存区...
git add .

:: 提交
echo [3/4] 提交变更...
git commit -m "feat: 完善项目结构，添加专业 README" >nul 2>&1
if errorlevel 1 (
    echo [提示] 没有新的变更需要提交
) else (
    echo [提交成功]
)

:: 推送
echo [4/4] 推送到 GitHub...
echo.
echo [注意] 首次推送需要登录 GitHub，按提示操作即可
echo.
git push origin master

if errorlevel 1 (
    echo.
    echo [失败] 推送失败，可能原因：
    echo   1. 需要登录 GitHub（按提示操作）
    echo   2. 本地与远程有冲突（先运行：git pul origin master）
    echo   3. 没有仓库写入权限
    echo.
    echo 也可以手动推送：
    echo   git push -u origin master
) else (
    echo.
    echo ================================
    echo  [成功] 已推送到 GitHub！
    echo  仓库地址：https://github.com/try-brave/cuddly-octo-spoon
    echo ================================
)

paus

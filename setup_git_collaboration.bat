@echo off
title Git Collaboration Setup

set "REMOTE_URL=请替换成你的远程仓库地址"

if "%REMOTE_URL%"=="请替换成你的远程仓库地址" (
    echo [ERROR] Please edit this file first and replace REMOTE_URL with your real Git repository URL.
    pause
    exit /b 1
)

echo Initializing Git repository...
git init -b main
if errorlevel 1 exit /b 1

echo Adding project files...
git add .
if errorlevel 1 exit /b 1

echo Creating initial commit...
git commit -m "Initial commit: table tennis training monitoring system"

echo Configuring remote origin...
git remote remove origin 2>nul
git remote add origin "%REMOTE_URL%"
if errorlevel 1 exit /b 1

echo Pushing main branch...
git push -u origin main
if errorlevel 1 exit /b 1

echo Creating develop branch...
git checkout -b develop
git push -u origin develop
if errorlevel 1 exit /b 1

echo Creating collaboration branches...
for %%B in (
    feature/auth-permission
    feature/player-query
    feature/training-import
    feature/dashboard-echarts
    feature/injury-rehab
    feature/fitness-test
    feature/match-report
    feature/system-settings
    docs/deployment-guide
) do (
    git checkout develop
    git checkout -b %%B
    git push -u origin %%B
)

git checkout develop

echo.
echo Done. Repository and collaboration branches have been pushed.
echo Current branch: develop
pause

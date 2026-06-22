@echo off
setlocal
set REPO_ROOT=%~dp0\..
powershell -ExecutionPolicy Bypass -File "%~dp0bootstrap_windows.ps1" -RepoRoot "%REPO_ROOT%"

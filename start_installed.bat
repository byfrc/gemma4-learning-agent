@echo off
setlocal

call "%~dp0start_windows.bat" -SkipInstall %*
exit /b %ERRORLEVEL%

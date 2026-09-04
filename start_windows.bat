@echo off
setlocal

call "%~dp0app\deploy\start_windows.bat" %*
exit /b %ERRORLEVEL%

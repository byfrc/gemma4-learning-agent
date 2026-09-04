@echo off
setlocal

call "%~dp0app\deploy\start_lmstudio_windows.bat" %*
exit /b %ERRORLEVEL%

@echo off
setlocal

call "%~dp0app\deploy\stop_windows.bat" %*
exit /b %ERRORLEVEL%

@echo off
rem cinemokhwa CLI launcher - uses the embedded Python from ComfyUI Portable.
rem Keep this file ASCII-only: cmd.exe parses .cmd in the OEM code page.
setlocal
if "%PYTHONIOENCODING%"=="" set PYTHONIOENCODING=utf-8
if "%PYTHONUTF8%"=="" set PYTHONUTF8=1
if "%CINEMOKHWA_ROOT%"=="" set CINEMOKHWA_ROOT=C:\Users\mbc\mokhwa
"%CINEMOKHWA_ROOT%\ComfyUI_windows_portable\python_embeded\python.exe" -s "%~dp0cli.py" %*
exit /b %ERRORLEVEL%

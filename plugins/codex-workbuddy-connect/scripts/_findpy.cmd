@echo off
rem 供其它脚本 call：在 PYEXE 里放一个可用的 python 解释器。
rem 优先级：WORKBUDDY_AI_PYTHON > Hermes venv > 常见安装路径 > PATH。
rem 本文件必须保持 GBK(cp936) + CRLF。
set "PYEXE="
if defined WORKBUDDY_AI_PYTHON if exist "%WORKBUDDY_AI_PYTHON%" set "PYEXE=%WORKBUDDY_AI_PYTHON%"
if not defined PYEXE if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe" set "PYEXE=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PYEXE if exist "%ProgramFiles%\Python313\python.exe" set "PYEXE=%ProgramFiles%\Python313\python.exe"
if not defined PYEXE if exist "%ProgramFiles%\Python312\python.exe" set "PYEXE=%ProgramFiles%\Python312\python.exe"
if not defined PYEXE if exist "%ProgramFiles%\Python311\python.exe" set "PYEXE=%ProgramFiles%\Python311\python.exe"
if not defined PYEXE for /f "delims=" %%i in ('where python 2^>NUL') do if not defined PYEXE set "PYEXE=%%i"
exit /b 0

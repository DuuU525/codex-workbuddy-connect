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
rem
rem 同时给出「无控制台」解释器 PYWEXE：优先与 PYEXE 同目录的 pythonw.exe。
rem 为什么需要：venv 的 python.exe 是 uv 启动器存根，它重新 spawn
rem pyvenv.cfg 里 home 指向的真实解释器时**不传递 creationflags**，
rem 真实进程于是自建一个可见的控制台窗口（实测踩过）。改走 pythonw 存根即无窗口。
set "PYWDIR="
set "PYWEXE="
if defined PYEXE for %%d in ("%PYEXE%") do set "PYWDIR=%%~dpd"
if defined PYWDIR if exist "%PYWDIR%pythonw.exe" set "PYWEXE=%PYWDIR%pythonw.exe"
if not defined PYWEXE set "PYWEXE=%PYEXE%"
exit /b 0

@echo off
rem Verifies harness assumptions on the target (wait/alias timing, status format,
rem menuselect, connect log line, buffer survival across changelevel). ~1 min.
rem Usage: probe.bat <game_dir>
set GAMEDIR=%1
if "%GAMEDIR%"=="" set GAMEDIR=.
if not exist "%GAMEDIR%\hl.exe" goto nohl
if exist "%GAMEDIR%\cstrike\qconsole.log" del "%GAMEDIR%\cstrike\qconsole.log"
if exist "%GAMEDIR%\podbot.log" del "%GAMEDIR%\podbot.log"
if exist "%GAMEDIR%\PODERROR.txt" del "%GAMEDIR%\PODERROR.txt"
copy /y "%~dp0cstrike\smoketest_probe.cfg" "%GAMEDIR%\cstrike\smoketest_probe.cfg" >nul
cd /d "%GAMEDIR%"
hl.exe -game cstrike -console -condebug -dev +maxplayers 8 +map de_dust2 +exec smoketest_probe.cfg
echo.
echo ---- probe markers ----
findstr /c:"[PROBE]" cstrike\qconsole.log
echo ---- connect lines (expect: connected, address "none" for the bot) ----
findstr /c:"connected, address" cstrike\qconsole.log
echo ---- status rows ----
findstr /r /c:"^# *[0-9]" cstrike\qconsole.log
if exist PODERROR.txt echo PODERROR.txt present!
goto end
:nohl
echo hl.exe not found in "%GAMEDIR%".
:end

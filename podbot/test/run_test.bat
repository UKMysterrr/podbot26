@echo off
rem POD-Bot smoke test runner (final WON CS 1.6, listen server).
rem Usage: run_test.bat [game_dir] [map] [lan_ip]
rem   game_dir  folder containing hl.exe (default: current folder)
rem   map       start map (default: de_dust2)
rem Covers criterion 1 (clean boot via +map, no PODERROR.txt) and drives
rem criteria 2-13 through cstrike\smoketest.cfg. Results: parse_results.py.

set GAMEDIR=%1
if "%GAMEDIR%"=="" set GAMEDIR=.
set MAP=%2
if "%MAP%"=="" set MAP=de_dust2

if not exist "%GAMEDIR%\hl.exe" goto nohl

rem Always purge old logs first.
if exist "%GAMEDIR%\podbot.log" del "%GAMEDIR%\podbot.log"
if exist "%GAMEDIR%\PODERROR.txt" del "%GAMEDIR%\PODERROR.txt"
if exist "%GAMEDIR%\cstrike\podbot.log" del "%GAMEDIR%\cstrike\podbot.log"
if exist "%GAMEDIR%\cstrike\PODERROR.txt" del "%GAMEDIR%\cstrike\PODERROR.txt"
if exist "%GAMEDIR%\cstrike\qconsole.log" del "%GAMEDIR%\cstrike\qconsole.log"

if exist "%GAMEDIR%\cstrike\qconsole_phase1.log" del "%GAMEDIR%\cstrike\qconsole_phase1.log"
if exist "%GAMEDIR%\cstrike\qconsole_phase2.log" del "%GAMEDIR%\cstrike\qconsole_phase2.log"
if exist "%GAMEDIR%\cstrike\smoketest_phase2_noclient.txt" del "%GAMEDIR%\cstrike\smoketest_phase2_noclient.txt"
if exist "%GAMEDIR%\podbot_phase1.log" del "%GAMEDIR%\podbot_phase1.log"
if exist "%GAMEDIR%\PODERROR_phase1.txt" del "%GAMEDIR%\PODERROR_phase1.txt"

rem Install the test config next to the game's own configs.
if exist "%~dp0cstrike\smoketest.cfg" copy /y "%~dp0cstrike\smoketest.cfg" "%GAMEDIR%\cstrike\smoketest.cfg" >nul
if not exist "%GAMEDIR%\cstrike\smoketest.cfg" goto nocfg

rem -condebug writes cstrike\qconsole.log; developer 1 is set in the cfg too.
rem -num_edicts raises the edict limit; maxplayers 32 for the capacity step.
cd /d "%GAMEDIR%"
hl.exe -game cstrike -console -condebug -dev -num_edicts 900 -heapsize 256000 +maxplayers 32 +map %MAP% +exec smoketest.cfg

echo.
echo Phase 1 exited (code %ERRORLEVEL%).

rem Keep phase-1 logs; phase 2 then starts from a purged directory.
if exist "%GAMEDIR%\cstrike\qconsole.log" move /y "%GAMEDIR%\cstrike\qconsole.log" "%GAMEDIR%\cstrike\qconsole_phase1.log" >nul
if exist "%GAMEDIR%\podbot.log" move /y "%GAMEDIR%\podbot.log" "%GAMEDIR%\podbot_phase1.log" >nul
if exist "%GAMEDIR%\PODERROR.txt" move /y "%GAMEDIR%\PODERROR.txt" "%GAMEDIR%\PODERROR_phase1.txt" >nul

rem ---- Phase 2 (criterion 11): real client on a network address vs. a full server ----
rem Usage: set SKIP_PHASE2=1 to skip. Optional 3rd argument: this PC's LAN IPv4.
if "%SKIP_PHASE2%"=="1" goto parse
set LANIP=%3
if "%LANIP%"=="" for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do if not defined LANIP set LANIP=%%a
if "%LANIP%"=="" goto noip
set LANIP=%LANIP: =%
echo Phase 2: server on %LANIP%:27015, client connects via that address.

rem Purge again so phase 2 logs are clean.
if exist "%GAMEDIR%\podbot.log" del "%GAMEDIR%\podbot.log"
if exist "%GAMEDIR%\PODERROR.txt" del "%GAMEDIR%\PODERROR.txt"
if exist "%GAMEDIR%\cstrike\qconsole.log" del "%GAMEDIR%\cstrike\qconsole.log"
if exist "%GAMEDIR%\cstrike\smoketest_phase2_noclient.txt" del "%GAMEDIR%\cstrike\smoketest_phase2_noclient.txt"
copy /y "%~dp0cstrike\smoketest_slots.cfg" "%GAMEDIR%\cstrike\smoketest_slots.cfg" >nul
copy /y "%~dp0cstrike\smoketest_client.cfg" "%GAMEDIR%\cstrike\smoketest_client.cfg" >nul
echo alias srvconnect "connect %LANIP%:27015"> "%GAMEDIR%\cstrike\smoketest_client_ip.cfg"

rem Server (listen host, 8 slots). Windowed so the second instance can coexist.
rem CLIENT_ARGS: extra hl.exe flags for the second instance (set before running).
rem No flag that disables the single-instance check is assumed; the check below
rem reports if WON refuses a second hl.exe, and phase 2 then stays MANUAL.
set BASEARGS=-game cstrike -console -window
start "podbot-server" /d "%GAMEDIR%" hl.exe %BASEARGS% -condebug -dev -num_edicts 900 +maxplayers 8 +port 27015 +map de_dust2 +exec smoketest_slots.cfg

rem ~70 s for map load + bot fill (ping is the portable sleep), then start the client.
ping -n 71 127.0.0.1 >nul
start "podbot-client" /d "%GAMEDIR%" hl.exe %BASEARGS% %CLIENT_ARGS% +exec smoketest_client.cfg

rem Diagnostic: after 20 s there must be two hl.exe processes (server + client).
ping -n 21 127.0.0.1 >nul
set NPROC=0
for /f %%n in ('tasklist /fi "imagename eq hl.exe" 2^>nul ^| find /c /i "hl.exe"') do set NPROC=%%n
if "%NPROC%"=="2" goto twook
echo WARNING: %NPROC% hl.exe process(es) running, expected 2. The second instance was probably refused.
echo Phase 2 cannot be validated on this PC; run the client on another machine against %LANIP%:27015.
echo second instance not running> "%GAMEDIR%\cstrike\smoketest_phase2_noclient.txt"
:twook

rem Wait for the server to finish: it quits itself after ~4.5 min. Poll the
rem completion marker, 15 s steps, 40 steps (10 min) maximum.
set /a TRIES=0
:waitserver
ping -n 16 127.0.0.1 >nul
set /a TRIES+=1
findstr /c:"[SMOKE] STEP 11B END" "%GAMEDIR%\cstrike\qconsole.log" >nul 2>&1
if not errorlevel 1 goto serverdone
if %TRIES% GEQ 40 goto servertimeout
goto waitserver
:servertimeout
echo Phase 2 server did not reach STEP 11B END within 10 minutes; close its window manually.
:serverdone
ping -n 11 127.0.0.1 >nul
if exist "%GAMEDIR%\cstrike\qconsole.log" copy /y "%GAMEDIR%\cstrike\qconsole.log" "%GAMEDIR%\cstrike\qconsole_phase2.log" >nul
goto parse

:noip
echo Could not detect a LAN IPv4; skipping phase 2 (pass it as the 3rd argument).

:parse
echo Parsing results...
python "%~dp0..\..\parse_results.py" "%GAMEDIR%"
goto end

:nohl
echo hl.exe not found in "%GAMEDIR%". Pass the game folder as the first argument.
goto end
:nocfg
echo smoketest.cfg missing. Keep run_test.bat next to its cstrike folder.
:end

@echo off
setlocal
rem ============================================================================
rem  OpenSim Run - one launcher for both runs
rem    1) WITHOUT actuator : OpenSim_Project\Scripts\run_opensim_knee_SO.py
rem    2) Quick test (12)  : OpenSim_Project\Scripts\run_opensim_QUICK_TEST_12.py
rem    3) WITH actuator    : Actuator_Run\Scripts\run_actuator_bag_SO.py
rem    4) Both (1 then 3)
rem  Uses the Jython + Java that ship with OpenSim 4.6 (no Python needed).
rem  Change OSIM below if OpenSim 4.6 is installed somewhere else.
rem  Keep this folder on a path with English letters only.
rem ============================================================================
set "OSIM=C:\OpenSim 4.6"
set "HERE=%~dp0"
set "PATH=%OSIM%\bin;%PATH%"

if not exist "%OSIM%\jdk\jre\bin\java.exe" (
    echo ERROR: OpenSim 4.6 not found in "%OSIM%".
    echo Open this file in a text editor and set OSIM to your OpenSim 4.6 folder.
    pause
    exit /b 1
)

set "CHOICE=%~1"
if not "%CHOICE%"=="" goto dispatch

echo.
echo  ================= OpenSim Run =================
echo   1  Run WITHOUT actuator  (OpenSim_Project, 116 conditions)
echo   2  Quick test WITHOUT actuator (12 conditions)
echo   3  Run WITH actuator     (Actuator_Run, 44 conditions)
echo   4  Run both (1 then 3)
echo   0  Exit
echo  ===============================================
set /p "CHOICE=Choose 1-4: "

:dispatch
if "%CHOICE%"=="1" call :run "%HERE%OpenSim_Project\Scripts\run_opensim_knee_SO.py"      "%HERE%OpenSim_Project\Results\OpenSim_SO" & goto end
if "%CHOICE%"=="2" call :run "%HERE%OpenSim_Project\Scripts\run_opensim_QUICK_TEST_12.py" "%HERE%OpenSim_Project\Results\OpenSim_SO" & goto end
if "%CHOICE%"=="3" call :run "%HERE%Actuator_Run\Scripts\run_actuator_bag_SO.py"         "%HERE%Actuator_Run\Results" & goto end
if "%CHOICE%"=="4" (
    call :run "%HERE%OpenSim_Project\Scripts\run_opensim_knee_SO.py" "%HERE%OpenSim_Project\Results\OpenSim_SO"
    call :run "%HERE%Actuator_Run\Scripts\run_actuator_bag_SO.py"    "%HERE%Actuator_Run\Results"
    goto end
)
if "%CHOICE%"=="0" exit /b 0
echo Invalid choice: %CHOICE%
goto end

:run
echo.
echo ---- Running %~nx1 ----
if not exist "%HERE%jycache" mkdir "%HERE%jycache"
pushd "%~dp1"
"%OSIM%\jdk\jre\bin\java.exe" -Xmx2g "-Djava.library.path=%OSIM%\bin" -Dpython.cachedir.skip=false "-Dpython.cachedir=%HERE%jycache" -Dpython.console.encoding=cp1252 -cp "%OSIM%\opensim\modules\ext\jython.jar;%OSIM%\opensim\modules\org-opensim-modeling.jar" org.python.util.jython "%~1"
popd
echo Done. Results are in "%~2"  (log: run_log.txt)
exit /b 0

:end
echo.
pause
endlocal

@echo off
rem Runs Scripts\run_actuator_bag_SO.py with the Jython + Java that ship with OpenSim 4.6 (no Python needed).
rem Change OSIM if OpenSim 4.6 is installed somewhere else.
set "OSIM=C:\OpenSim 4.6"
set "HERE=%~dp0"
set "PATH=%OSIM%\bin;%PATH%"
if not exist "%HERE%jycache" mkdir "%HERE%jycache"
"%OSIM%\jdk\jre\bin\java.exe" -Xmx2g "-Djava.library.path=%OSIM%\bin" -Dpython.cachedir.skip=false "-Dpython.cachedir=%HERE%jycache" -Dpython.console.encoding=cp1252 -cp "%OSIM%\opensim\modules\ext\jython.jar;%OSIM%\opensim\modules\org-opensim-modeling.jar" org.python.util.jython "%HERE%Scripts\run_actuator_bag_SO.py"
echo.
echo Done. Results are in "%HERE%Results"  (log: Results\run_log.txt)
pause

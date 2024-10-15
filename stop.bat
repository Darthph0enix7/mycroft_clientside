@echo off
echo Stopping all Python processes...

:: Find and terminate all python.exe processes
for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH') do (
    echo Terminating process with PID %%i
    taskkill /PID %%i /F
)

:: Find and terminate all pythonw.exe processes
for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH') do (
    echo Terminating process with PID %%i
    taskkill /PID %%i /F
)

echo All Python processes have been stopped.
@echo off
REM Clear Python cache and run tests

echo ========================================
echo Clearing Python cache...
echo ========================================

cd /d "%~dp0"

REM Delete all __pycache__ directories
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Delete all .pyc files
del /s /q *.pyc 2>nul

echo Cache cleared!
echo.
echo ========================================
echo Running tests...
echo ========================================
echo.

cd ..
pytest agentcore/tests/test_agent_basic.py -v -s --tb=short

pause

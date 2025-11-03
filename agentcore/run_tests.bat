@echo off
REM Quick test runner for RepoIntegrator
REM Run from agentcore directory or project root

echo ========================================
echo Running RepoIntegrator Tests
echo ========================================
echo.

cd /d "%~dp0.."
echo Current directory: %CD%
echo.

echo Running pytest...
pytest agentcore/tests/test_agent_basic.py -v -s

echo.
echo ========================================
echo Test run complete!
echo ========================================
pause

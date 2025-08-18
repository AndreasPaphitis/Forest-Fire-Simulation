@echo off
echo ========================================
echo Local Forest Fire Simulation Tests
echo ========================================
echo.

echo Creating test output directories...
if not exist "test_output" mkdir test_output
if not exist "test_output\local_calibration" mkdir test_output\local_calibration
if not exist "test_output\local_calibration_results" mkdir test_output\local_calibration_results

echo.
echo ========================================
echo Test 1: Single Simulation Test
echo ========================================
echo This will test a single simulation to isolate the list.items() error
echo.
python scripts/test_single_simulation.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Single simulation test FAILED
    echo Check test_output/single_simulation_test.log for details
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Single simulation test PASSED
    echo.
)

echo.
echo ========================================
echo Test 2: Local Calibration Test
echo ========================================
echo This will run a minimal calibration to reproduce the list.items() error
echo.
python scripts/test_local_calibration.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Local calibration test FAILED
    echo Check test_output/local_calibration_test.log for details
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Local calibration test PASSED
    echo.
)

echo.
echo ========================================
echo All tests completed!
echo ========================================
echo Check the test_output directory for detailed logs
echo.
pause

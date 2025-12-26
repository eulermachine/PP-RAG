@echo off
setlocal

echo ==============================================
echo Building PP-RAG HE Core Module (Real SEAL CKKS)
echo ==============================================

if not exist build (
    mkdir build
)

cd build

echo [1/3] Configuring CMake...
cmake .. -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] CMake configuration failed.
    echo Please ensure you have CMake and Microsoft SEAL installed and discoverable.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Building...
cmake --build . --config Release
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed.
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Installing module...
REM Copy the generated pyd file to root src directory or where python can find it
REM For this project structure, bench_runner expects pprag_core to be importable.
REM Python adds current directory to path, so copying to project root is simplest.
cd ..
copy /Y build\Release\pprag_core*.pyd . >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not copy .pyd file from build/Release. Try checking build directory.
    copy /Y build\pprag_core*.pyd . >nul
)

echo.
echo ==============================================
echo Build Complete!
echo You can now run the benchmarks:
echo   python scripts/07_run_multiscale.py --scales 100k
echo ==============================================

endlocal

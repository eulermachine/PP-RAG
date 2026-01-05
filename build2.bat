@echo off
setlocal

echo ==============================================
echo Building PP-RAG HE Core Module - Variant 2
echo (Hybrid with Partial Client Decryption)
echo ==============================================

if not exist build2 (
    mkdir build2
)

cd build2

echo [1/3] Configuring CMake for Variant 2...
cmake .. -f ..\CMakeLists2.txt -DCMAKE_BUILD_TYPE=Release
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
cd ..
copy /Y build2\Release\pprag_core2*.pyd . >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not copy .pyd file from build2/Release. Try checking build2 directory.
    copy /Y build2\pprag_core2*.pyd . >nul
)

echo.
echo ==============================================
echo Build Complete for Variant 2!
echo You can now run the Variant 2 benchmarks:
echo   python scripts/05_run_all2.py
echo ==============================================

endlocal

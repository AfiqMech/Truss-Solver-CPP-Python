@echo off
chcp 65001 >nul
echo ===========================================
echo    TRUSS SOLVER 🏗️
echo ===========================================
echo.

:: Ensure we are running in the script's directory
cd /d "%~dp0"

:: --- STEP 1: DETECT PYTHON ---
set PYTHON_CMD=python

:: Try 'python' command
python --version >nul 2>&1
if %errorlevel% equ 0 goto :FOUND_PYTHON

:: Try 'py' command (Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND_PYTHON
)

:: Try 'python3' command
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :FOUND_PYTHON
)

:: IF WE GET HERE, PYTHON WAS NOT FOUND

:: --- ATTEMPT SMART RECOVERY (Missing Path) ---
:: Check LocalAppData (Standard User Install)
for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%i\python.exe" (
        echo.
        echo 🔍 Found Python in: "%%i"
        echo [AUTO-FIX] It was hidden from PATH. Using it temporarily...
        set "PYTHON_CMD=%%i\python.exe"
        set "PATH=%%i;%%i\Scripts;%PATH%"
        goto :FOUND_PYTHON
    )
)

:: Check Program Files (System Install)
for /d %%i in ("%ProgramFiles%\Python3*") do (
    if exist "%%i\python.exe" (
        echo.
        echo 🔍 Found Python in: "%%i"
        echo [AUTO-FIX] It was hidden from PATH. Using it temporarily...
        set "PYTHON_CMD=%%i\python.exe"
        set "PATH=%%i;%%i\Scripts;%PATH%"
        goto :FOUND_PYTHON
    )
)

echo ❌ [ERROR] Python really not found!
echo.
echo ----------------------------------------------------
echo  OPTION 1: AUTOMATIC INSTALL (Recommended)
echo ----------------------------------------------------
echo.
winget --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Winget detected. Attempting to install Python 3.12...
    echo.
    echo [INSTALL] requesting administrative privileges for installation...
    echo [INSTALL] running: winget install Python.Python.3.12
    echo.
    
    :: Install Python 3.12 silent, all users, add to path
    winget install -e --id Python.Python.3.12 --scope machine --accept-source-agreements --accept-package-agreements --override "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
    
    if %errorlevel% equ 0 (
        echo.
        echo ✅ Python installed successfully!
        echo.
        echo [IMPORTANT] We need to restart this script to apply changes...
        echo.
        pause
        start "Truss Solver" "%~f0"
        exit
    ) else (
        echo.
        echo ❌ Winget install failed. Please try manual install.
    )
) else (
    echo Winget not found. skipping auto-install.
)

echo.
echo ----------------------------------------------------
echo  OPTION 2: MANUAL INSTALL
echo ----------------------------------------------------
echo 1. Go to https://python.org/downloads/
echo 2. Download Python 3.12 (or newer)
echo 3. IMPORTANT: Check "Add Python to environment variables" (or PATH)
echo 4. Run this script again.
echo.
pause
exit /b

:FOUND_PYTHON
echo ✅ Found Python: %PYTHON_CMD%

:: --- STEP 2: SETUP ENVIRONMENT ---
if not exist ".venv" (
    echo [SETUP] Creating virtual environment... (This takes 1-2 mins)
    %PYTHON_CMD% -m venv .venv
    
    if not exist ".venv\Scripts\pip.exe" (
        echo ❌ [ERROR] Failed to create .venv. properly. 
        echo Please try deleting the .venv folder and running again.
        pause
        exit /b
    )

    echo [SETUP] Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt >nul
    echo ✅ Setup Complete!
)

:: --- STEP 3: RUN APP ---
echo [RUN] Launching Application...
if exist ".venv\Scripts\streamlit.exe" (
    .venv\Scripts\streamlit run app.py
) else (
    echo ❌ [ERROR] Streamlit not found in .venv.
    echo Attempting repair...
    .venv\Scripts\pip install -r requirements.txt
    .venv\Scripts\streamlit run app.py
)

pause

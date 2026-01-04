@echo off
setlocal

:: Get Addon ID and Version from addon.xml using PowerShell
for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "$xml=[xml](Get-Content addon.xml); Write-Output $xml.addon.id"`) do set "ADDON_ID=%%A"
for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "$xml=[xml](Get-Content addon.xml); Write-Output $xml.addon.version"`) do set "ADDON_VER=%%A"

if "%ADDON_ID%"=="" (
    echo Error: Could not extract addon ID.
    pause
    exit /b 1
)
if "%ADDON_VER%"=="" (
    echo Error: Could not extract addon version.
    pause
    exit /b 1
)

echo Building release for %ADDON_ID% v%ADDON_VER%...

set "RELEASE_DIR=%~dp0releases"
set "ZIP_NAME=%ADDON_ID%-%ADDON_VER%.zip"
set "TEMP_DIR=%TEMP%\%ADDON_ID%_build"
set "BUILD_ROOT=%TEMP_DIR%\%ADDON_ID%"

:: Clean up temp and release
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
if exist "%RELEASE_DIR%\%ZIP_NAME%" del "%RELEASE_DIR%\%ZIP_NAME%"

:: Create build structure
mkdir "%BUILD_ROOT%"

echo Copying whitelisted content...

set "FILES_TO_COPY=addon.xml service.py script.py LICENSE README.md icon.png"
set "DIRS_TO_COPY=resources"

:: Copy Files
for %%f in (%FILES_TO_COPY%) do (
    if exist "%%f" (
        xcopy "%%f" "%BUILD_ROOT%\" /Y
    )
)

:: Create Exclude File for Directories
set "EXCLUDE_FILE=%TEMP%\xcopy_excludes.txt"
(
    echo __pycache__
    echo .pyc
) > "%EXCLUDE_FILE%"

:: Copy Directories
for %%d in (%DIRS_TO_COPY%) do (
    if exist "%%d" (
        xcopy "%%d" "%BUILD_ROOT%\%%d" /E /I /Y /EXCLUDE:%EXCLUDE_FILE%
    )
)

del "%EXCLUDE_FILE%"

:: Create Zip using PowerShell
echo Creating zip package...
pushd "%TEMP_DIR%"
7z a -tzip -mx=0 "%RELEASE_DIR%\%ZIP_NAME%" "%ADDON_ID%"
popd

:: Cleanup
rmdir /s /q "%TEMP_DIR%"

echo.
echo SUCCESS: Created release package at %RELEASE_DIR%\%ZIP_NAME%
timeout /t 5

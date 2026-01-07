@echo off
setlocal



:: Target Directory (Standard Windows Install)
for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "$xml=[xml](Get-Content addon.xml); Write-Output $xml.addon.id"`) do set "ADDON_ID=%%A"
set "TARGET_DIR=%APPDATA%\Kodi\addons\%ADDON_ID%"

echo Deploying NFO Sync to %TARGET_DIR%

if not exist "%TARGET_DIR%" (
    echo Target directory not found: "%TARGET_DIR%"
    echo Creating it...
    mkdir "%TARGET_DIR%"
)

:: Files to Copy
set FILES_TO_COPY=
set FILES_TO_COPY=%FILES_TO_COPY% addon.xml
set FILES_TO_COPY=%FILES_TO_COPY% service.py
set FILES_TO_COPY=%FILES_TO_COPY% script.py
set FILES_TO_COPY=%FILES_TO_COPY% LICENSE
set FILES_TO_COPY=%FILES_TO_COPY% README.md
set FILES_TO_COPY=%FILES_TO_COPY% icon.png

:: Directories to Copy
set DIRS_TO_COPY=
set DIRS_TO_COPY=%DIRS_TO_COPY% resources

:: Excluded Files
set EXCLUDE_FILE=%TEMP%\xcopy_excludes.txt
(
    echo __pycache__
    echo .pyc
) > "%EXCLUDE_FILE%"

echo.
echo Copying Files...
for %%f in (%FILES_TO_COPY%) do (
    if exist "%%f" (
        echo Copying %%f
        xcopy "%%f" "%TARGET_DIR%\" /Y /H /Q /R >nul
    )
)
echo.
echo Copying Directories...
for %%d in (%DIRS_TO_COPY%) do (
    if exist "%%d" (
        echo Copying %%d directory
        xcopy "%%d" "%TARGET_DIR%\%%d" /E /I /Y /EXCLUDE:%EXCLUDE_FILE% /Q /H /R >nul
    )
)

del "%EXCLUDE_FILE%"

echo.
echo Deployment Complete!
echo You may need to restart Kodi or Reload the skin/addon for changes to take effect.
timeout /t 5
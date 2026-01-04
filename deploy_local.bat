@echo off
setlocal

echo Deploying NFO Sync to Kodi Addons folder...

:: Target Directory (Standard Windows Install)
set "TARGET_DIR=%APPDATA%\Kodi\addons\service.library.nfosync"

if not exist "%TARGET_DIR%" (
    echo Target directory not found: "%TARGET_DIR%"
    echo Creating it...
    mkdir "%TARGET_DIR%"
)

set "FILES_TO_COPY=addon.xml service.py script.py LICENSE README.md icon.png"
set "DIRS_TO_COPY=resources"

:: Create Exclude File
set "EXCLUDE_FILE=%TEMP%\xcopy_excludes.txt"
(
    echo __pycache__
    echo .pyc
) > "%EXCLUDE_FILE%"

echo Copying Files...
for %%f in (%FILES_TO_COPY%) do (
    if exist "%%f" (
        echo Copying %%f
        xcopy "%%f" "%TARGET_DIR%\" /Y /Q
    )
)

echo Copying Directories...
for %%d in (%DIRS_TO_COPY%) do (
    if exist "%%d" (
        echo Copying %%d
        xcopy "%%d" "%TARGET_DIR%\%%d" /E /I /Y /EXCLUDE:%EXCLUDE_FILE% /Q
    )
)

del "%EXCLUDE_FILE%"

echo.
echo Deployment Complete!
echo You may need to restart Kodi or Reload the skin/addon for changes to take effect.
pause

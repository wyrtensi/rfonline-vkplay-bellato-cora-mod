@echo off
chcp 65001 >nul
title RF Online Cora-Bellato Mod 1-Click Restore
echo ====================================================================
echo  RF Online 4.75 Cora ^<--^> Bellato Mod Restorer (1-Second Recovery)
echo ====================================================================
echo.
if not exist "_ModCache" (
    echo [ERROR] _ModCache directory not found!
    echo Please run 'python cora_bellato_patcher.py --apply' first.
    pause
    exit /b 1
)
echo [*] Restoring mod files from _ModCache into game directory...
robocopy "_ModCache" "." /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np >nul
if errorlevel 8 (
    echo [!] Robocopy reported errors. Falling back to xcopy...
    xcopy /S /Y /Q "_ModCache\*.*" ".\" >nul
)
echo [+]
echo [+] SUCCESS! Mod applied successfully in 1 click.
echo [+] You can now launch RF Online via Innova 4game Launcher.
echo.
ping 127.0.0.1 -n 3 >nul 2>&1

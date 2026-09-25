# RF Online Cora <-> Bellato Mod 1-Click Restore
$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = 'RF Online Cora-Bellato Mod 1-Click Restore'
Write-Host '====================================================================' -ForegroundColor Cyan
Write-Host ' RF Online 4.75 Cora <-> Bellato Mod Restorer (1-Second Recovery)' -ForegroundColor Yellow
Write-Host '====================================================================' -ForegroundColor Cyan
Write-Host ''
if (-not (Test-Path '_ModCache')) {
    Write-Host '[ERROR] _ModCache directory not found!' -ForegroundColor Red
    Write-Host 'Please run python cora_bellato_patcher.py --apply first.' -ForegroundColor White
    exit 1
}
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host '[*] Restoring mod files from _ModCache...' -ForegroundColor Gray
& robocopy '_ModCache' '.' /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Host '[!] Robocopy reported errors. Falling back to Copy-Item...' -ForegroundColor Yellow
    Copy-Item -Path '_ModCache\*' -Destination '.' -Recurse -Force
}
$sw.Stop()
Write-Host ('[+] SUCCESS! Mod restored in {0:N2} ms.' -f $sw.Elapsed.TotalMilliseconds) -ForegroundColor Green
Write-Host '[+] Ready to play! Launching client...' -ForegroundColor Green
Start-Sleep -Seconds 2

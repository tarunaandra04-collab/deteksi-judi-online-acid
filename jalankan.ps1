<#
  jalankan.ps1 -- satu perintah untuk demo di komputer lab.

    .\jalankan.ps1                 # install (jika perlu) -> start backend -> buka Edge dengan ekstensi termuat
    .\jalankan.ps1 -NoBrowser      # hanya backend
    .\jalankan.ps1 -Browser chrome # pakai Chrome
    .\jalankan.ps1 -Stop           # hentikan backend yang dijalankan skrip ini
    .\jalankan.ps1 -Url https://contoh.ac.id

  Browser dibuka dengan profil terpisah (folder .browser-profile) sehingga tidak mengganggu profil
  pengguna lain di komputer lab. Jika browser menolak --load-extension (kebijakan versi baru),
  skrip menampilkan cara manual (Load unpacked) -- lihat docs/PANDUAN_LAB.md.
#>
param(
    [switch]$NoBrowser,
    [switch]$Stop,
    [ValidateSet("edge", "chrome")][string]$Browser = "edge",
    [string]$Url = "https://www.ui.ac.id",
    [int]$Port = 5000
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$PidFile = Join-Path $Root ".backend.pid"
$LogFile = Join-Path $Root "backend.log"
$ExtDir = Join-Path $Root "extension"

function Stop-Backend {
    if (Test-Path $PidFile) {
        $p = [int](Get-Content $PidFile)
        if (Get-Process -Id $p -ErrorAction SilentlyContinue) { Stop-Process -Id $p -Force; Write-Host "[jalankan] Backend (PID $p) dihentikan." }
        Remove-Item $PidFile -Force
    } else { Write-Host "[jalankan] Tidak ada backend yang tercatat berjalan." }
}
if ($Stop) { Stop-Backend; exit 0 }

if (-not (Test-Path $VenvPy)) {
    Write-Host "[jalankan] Pertama kali: menyiapkan lingkungan Python..." -ForegroundColor Cyan
    & (Join-Path $Root "scripts\install.ps1")
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
if (-not (Test-Path (Join-Path $ExtDir "lexicon.js"))) { & $VenvPy (Join-Path $Root "scripts\build_assets.py") }

# --- backend ---
$health = "http://127.0.0.1:$Port/health"
$up = $false
try { $r = Invoke-RestMethod $health -TimeoutSec 2; $up = $true } catch { }
if ($up) {
    Write-Host "[jalankan] Backend sudah berjalan di port $Port." -ForegroundColor Yellow
} else {
    Write-Host "[jalankan] Menyalakan backend (port $Port)..."
    $env:DJO_PORT = "$Port"
    $proc = Start-Process -FilePath $VenvPy -ArgumentList "`"$(Join-Path $Root 'backend\app.py')`"" `
        -WorkingDirectory (Join-Path $Root "backend") -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $LogFile -RedirectStandardError "$LogFile.err"
    $proc.Id | Set-Content $PidFile
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1
        if ($proc.HasExited) { break }
        try { $r = Invoke-RestMethod $health -TimeoutSec 2; $up = $true; break } catch { }
    }
    if (-not $up) {
        Write-Host "[jalankan] Backend gagal start. Log:" -ForegroundColor Red
        if (Test-Path "$LogFile.err") { Get-Content "$LogFile.err" -Tail 25 }
        exit 1
    }
}
$info = Invoke-RestMethod $health
Write-Host ("[jalankan] Backend siap. Model: {0} | scikit-learn saat training: {1}" -f ($info.models -join ", "), $info.trained_with.sklearn) -ForegroundColor Green
if (-not $info.model_loaded) { Write-Host "[jalankan] PERINGATAN: model belum termuat -> $($info.error)" -ForegroundColor Red }

if ($NoBrowser) { Write-Host "[jalankan] Mode -NoBrowser. Muat ekstensi manual dari: $ExtDir"; exit 0 }

# --- browser ---
$candidates = if ($Browser -eq "edge") {
    @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe")
} else {
    @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
}
$exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) { Write-Host "[jalankan] $Browser tidak ditemukan. Muat ekstensi manual dari: $ExtDir" -ForegroundColor Yellow; exit 0 }

$profDir = Join-Path $Root ".browser-profile"
$launchArgs = @(
    "--user-data-dir=`"$profDir`"",
    "--load-extension=`"$ExtDir`"",
    "--disable-features=DisableLoadExtensionCommandLineSwitch",
    "--no-first-run", "--no-default-browser-check",
    $Url
)
Start-Process -FilePath $exe -ArgumentList $launchArgs
Write-Host "[jalankan] $Browser dibuka dengan ekstensi termuat. Buka halaman .ac.id lalu lihat ikon perisai di toolbar." -ForegroundColor Green
Write-Host "[jalankan] Jika ikon tidak muncul: buka ${Browser}://extensions -> aktifkan Developer mode -> Load unpacked -> pilih $ExtDir" -ForegroundColor Yellow
Write-Host "[jalankan] Hentikan backend nanti dengan: .\jalankan.ps1 -Stop"

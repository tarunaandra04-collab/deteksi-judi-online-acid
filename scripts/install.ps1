<#
  install.ps1 -- menyiapkan lingkungan Python untuk backend (sekali saja per komputer).
  Dijalankan otomatis oleh jalankan.ps1 bila .venv belum ada.

  Perlu: Python 3.11 atau lebih baru (diuji di 3.14) dan koneksi internet untuk pip.
#>
param([switch]$Force)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"

function Find-Python {
    $cands = @()
    foreach ($c in @("py -3", "python", "python3")) {
        $exe = $c.Split(" ")[0]
        if (Get-Command $exe -ErrorAction SilentlyContinue) { $cands += $c }
    }
    $local = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending
    foreach ($l in $local) { $cands += "`"$($l.FullName)`"" }
    foreach ($c in $cands) {
        try {
            $v = Invoke-Expression "$c -c `"import sys;print('%d.%d'%sys.version_info[:2])`"" 2>$null
            if ($v -and [version]$v -ge [version]"3.11") { return $c }
        } catch { }
    }
    return $null
}

if ((Test-Path $VenvPy) -and -not $Force) {
    Write-Host "[install] .venv sudah ada. Gunakan -Force untuk membuat ulang." -ForegroundColor Yellow
} else {
    $py = Find-Python
    if (-not $py) {
        Write-Host "[install] Python 3.11+ tidak ditemukan. Pasang dari https://www.python.org/downloads/ (centang 'Add python.exe to PATH')." -ForegroundColor Red
        exit 1
    }
    Write-Host "[install] Memakai Python: $py"
    if (Test-Path $Venv) { Remove-Item $Venv -Recurse -Force }
    Invoke-Expression "$py -m venv `"$Venv`""
}

Write-Host "[install] Memasang dependensi (butuh beberapa menit pertama kali)..."
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r (Join-Path $Root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { Write-Host "[install] pip gagal. Cek koneksi internet / versi Python." -ForegroundColor Red; exit 1 }

& $VenvPy (Join-Path $Root "scripts\build_assets.py")
& $VenvPy -c "import flask, sklearn, lightgbm, Sastrawi; print('[install] OK  scikit-learn', sklearn.__version__)"
Write-Host "[install] Selesai. Jalankan: .\jalankan.ps1" -ForegroundColor Green

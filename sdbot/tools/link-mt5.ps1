<#
.SYNOPSIS
    Hubungkan folder EA dan folder uji SDBot di repo ke folder data MT5 lewat junction.

.DESCRIPTION
    Membuat 7 junction di <DataDir>\MQL5\ yang menunjuk ke sdbot\ea\src dan sdbot\ea\tests.
    Semua junction diperiksa dulu; jika ada satu yang bentrok (folder biasa, atau junction
    ke tempat lain), skrip berhenti tanpa mengubah apa pun. Junction yang sudah benar dilewati.
    Tidak butuh Administrator. Jalankan sekali per terminal MT5 (live dan uji).

    Kode keluar: 0 = semua terhubung, 1 = ada bentrok, 2 = parameter/lingkungan salah.

.PARAMETER DataDir
    Folder data terminal MT5 (File -> Open Data Folder), yang berisi subfolder MQL5.

.PARAMETER RepoEa
    Folder sdbot\ea di repo. Default: ..\ea relatif ke lokasi skrip ini.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File sdbot\tools\link-mt5.ps1 -DataDir "C:\Users\me\AppData\Roaming\MetaQuotes\Terminal\<ID>"
#>
param(
    [Parameter(Mandatory = $true)][string]$DataDir,
    [string]$RepoEa = ''
)

$ErrorActionPreference = 'Stop'
# Di Windows PowerShell 5.1, $PSScriptRoot belum terisi saat default parameter dievaluasi.
if ([string]::IsNullOrEmpty($RepoEa)) { $RepoEa = Join-Path $PSScriptRoot '..\ea' }

# Junction yang dibuat: path relatif di dalam MQL5\  ->  path relatif di dalam sdbot\ea\
$links = @(
    @{ Link = 'Experts\SDBot';      Target = 'src\Experts\SDBot' },
    @{ Link = 'Include\SDBot';      Target = 'src\Include\SDBot' },
    @{ Link = 'Scripts\SDBot';      Target = 'src\Scripts\SDBot' },
    @{ Link = 'Presets\SDBot';      Target = 'src\Presets' },
    @{ Link = 'Experts\SDBotTests'; Target = 'tests\Experts\SDBotTests' },
    @{ Link = 'Include\SDBotTests'; Target = 'tests\Include\SDBotTests' },
    @{ Link = 'Scripts\SDBotTests'; Target = 'tests\Scripts\SDBotTests' }
)

function Normalize-PathText([string]$p) {
    # Target junction kadang dilaporkan dengan awalan \??\ ; samakan sebelum dibandingkan.
    if ($p.StartsWith('\??\')) { $p = $p.Substring(4) }
    return [IO.Path]::GetFullPath($p).TrimEnd('\')
}

$mql5 = Join-Path $DataDir 'MQL5'
if (-not (Test-Path -LiteralPath $mql5 -PathType Container)) {
    Write-Host "[link-mt5] ERROR: folder MQL5 tidak ditemukan di '$DataDir'. Isi -DataDir dengan folder dari MT5: File -> Open Data Folder."
    exit 2
}
if (-not (Test-Path -LiteralPath $RepoEa -PathType Container)) {
    Write-Host "[link-mt5] ERROR: folder repo EA tidak ditemukan: '$RepoEa'."
    exit 2
}
$RepoEa = Normalize-PathText (Resolve-Path -LiteralPath $RepoEa).Path

# Tahap 1: periksa semua tanpa mengubah apa pun.
$plan = @()
$conflicts = @()
foreach ($l in $links) {
    $linkPath = Join-Path $mql5 $l.Link
    $targetPath = Join-Path $RepoEa $l.Target
    if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
        Write-Host "[link-mt5] ERROR: target di repo tidak ada: '$targetPath'."
        exit 2
    }
    $targetNorm = Normalize-PathText $targetPath
    $item = Get-Item -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        $plan += @{ Link = $linkPath; Target = $targetNorm; Action = 'create' }
    }
    elseif ($item.LinkType -eq 'Junction' -or $item.LinkType -eq 'SymbolicLink') {
        $current = Normalize-PathText ([string]($item.Target | Select-Object -First 1))
        if ($current -ieq $targetNorm) {
            $plan += @{ Link = $linkPath; Target = $targetNorm; Action = 'ok' }
        }
        else {
            $conflicts += "junction '$linkPath' menunjuk ke '$current', bukan '$targetNorm'"
        }
    }
    else {
        $conflicts += "'$linkPath' adalah folder/file biasa, bukan junction (isinya tidak disentuh)"
    }
}

if ($conflicts.Count -gt 0) {
    Write-Host '[link-mt5] BENTROK, tidak ada yang diubah:'
    $conflicts | ForEach-Object { Write-Host "  - $_" }
    Write-Host '  Pindahkan atau hapus sendiri folder yang bentrok bila memang tidak dipakai, lalu jalankan ulang.'
    exit 1
}

# Tahap 2: buat junction yang belum ada.
foreach ($p in $plan) {
    if ($p.Action -eq 'ok') {
        Write-Host "[link-mt5] sudah terhubung: $($p.Link)"
        continue
    }
    $parent = Split-Path -Parent $p.Link
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    New-Item -ItemType Junction -Path $p.Link -Target $p.Target | Out-Null
    Write-Host "[link-mt5] dibuat: $($p.Link) -> $($p.Target)"
}
Write-Host "[link-mt5] selesai: $($plan.Count) junction terhubung ke $RepoEa"
exit 0

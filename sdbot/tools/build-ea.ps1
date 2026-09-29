<#
.SYNOPSIS
    Compile EA dan entry point uji SDBot lewat MetaEditor, dengan aturan 0 error dan 0 warning.

.DESCRIPTION
    Setiap target di-compile lewat path junction-nya di folder data terminal (lihat link-mt5.ps1),
    agar #include <SDBot/...> dan <SDBotTests/...> ter-resolve. Hasil dibaca dari baris
    "Result: N errors, M warnings" di log MetaEditor; exit code MetaEditor tidak dipakai karena
    tidak bisa diandalkan.

    Kode keluar: 0 = semua target 0 error 0 warning, 1 = ada error/warning atau tidak ada target,
    2 = konfigurasi/lingkungan belum siap.

.PARAMETER Target
    File .mq5 relatif ke sdbot\ea (misalnya src\Experts\SDBot\SDBot.mq5). Default: semua .mq5 di
    src\Experts\SDBot, src\Scripts\SDBot, tests\Experts\SDBotTests, tests\Scripts\SDBotTests.

.PARAMETER Terminal
    'test' (default) atau 'live': folder data mana yang dipakai untuk compile.

.PARAMETER Config
    Path mt5-paths.local.json. Default: sdbot\tools\mt5-paths.local.json.
#>
param(
    [string[]]$Target = @(),
    [ValidateSet('test', 'live')][string]$Terminal = 'test',
    [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\Mt5Paths.psm1') -Force

try {
    $cfg = Get-Mt5Config -Path $Config
}
catch {
    Write-Host "[build-ea] $($_.Exception.Message)"
    exit 2
}

$repoEa = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\ea'))
$dataDir = if ($Terminal -eq 'live') { $cfg.LiveDataDir } else { $cfg.TestDataDir }
$tmp = Join-Path $PSScriptRoot '.tmp'
if (-not (Test-Path -LiteralPath $tmp)) { New-Item -ItemType Directory -Path $tmp | Out-Null }

if ($Target.Count -eq 0) {
    $roots = 'src\Experts\SDBot', 'src\Scripts\SDBot', 'tests\Experts\SDBotTests', 'tests\Scripts\SDBotTests'
    $Target = foreach ($r in $roots) {
        $dir = Join-Path $repoEa $r
        if (Test-Path -LiteralPath $dir) {
            Get-ChildItem -LiteralPath $dir -Filter '*.mq5' -File | ForEach-Object { Join-Path $r $_.Name }
        }
    }
    $Target = @($Target)
}
if ($Target.Count -eq 0) {
    Write-Host '[build-ea] GAGAL: tidak ada file .mq5 untuk di-compile.'
    exit 1
}

$results = @()
foreach ($t in $Target) {
    $mt5Path = Convert-RepoPathToMt5 -RepoRelative $t -DataDir $dataDir
    if ($null -eq $mt5Path) {
        Write-Host "[build-ea] '$t' tidak berada di folder yang di-link ke MT5 (src\Experts\SDBot, src\Scripts\SDBot, tests\Experts\SDBotTests, tests\Scripts\SDBotTests)."
        exit 2
    }
    if (-not (Test-Path -LiteralPath (Join-Path $repoEa $t) -PathType Leaf)) {
        Write-Host "[build-ea] file tidak ada di repo: '$t'."
        exit 2
    }
    if (-not (Test-Path -LiteralPath $mt5Path -PathType Leaf)) {
        Write-Host "[build-ea] '$mt5Path' tidak terlihat dari folder data $Terminal. Jalankan: tools\link-mt5.ps1 -DataDir `"$dataDir`""
        exit 2
    }

    $name = [IO.Path]::GetFileNameWithoutExtension($t)
    $log = Join-Path $tmp "build-$name.log"
    if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
    $inc = Join-Path $dataDir 'MQL5'
    $meArgs = @("/compile:`"$mt5Path`"", "/inc:`"$inc`"", "/log:`"$log`"")
    Start-Process -FilePath $cfg.MetaEditor -ArgumentList $meArgs -Wait -WindowStyle Hidden | Out-Null

    $lines = @()
    if (Test-Path -LiteralPath $log) { $lines = @(Get-Content -LiteralPath $log -Encoding Unicode) }
    $resultLine = $lines | Where-Object { $_ -match 'Result:\s+(\d+)\s+errors?,\s+(\d+)\s+warnings?' } | Select-Object -Last 1
    # MetaEditor menulis setiap pesan dua kali di log; tampilkan sekali saja.
    $messages = @($lines | Where-Object { $_ -match ':\s+(error|warning)\s+\d+:' } | Select-Object -Unique)
    if ($resultLine -and $resultLine -match 'Result:\s+(\d+)\s+errors?,\s+(\d+)\s+warnings?') {
        $errors = [int]$Matches[1]; $warnings = [int]$Matches[2]
    }
    else {
        $errors = -1; $warnings = -1
        $messages += "(log MetaEditor tidak berisi baris Result; log: $log)"
    }
    $results += [pscustomobject]@{ Target = $t; Errors = $errors; Warnings = $warnings; Messages = $messages }
}

$failed = 0
foreach ($r in $results) {
    $ok = ($r.Errors -eq 0 -and $r.Warnings -eq 0)
    if (-not $ok) { $failed++ }
    $status = if ($ok) { 'OK  ' } else { 'FAIL' }
    Write-Host ("[build-ea] {0} {1}  errors={2} warnings={3}" -f $status, $r.Target, $r.Errors, $r.Warnings)
    foreach ($m in $r.Messages) {
        # Tampilkan path relatif agar pesan pendek dan menunjuk ke file di repo.
        Write-Host ("           " + ($m -replace [regex]::Escape($dataDir + '\'), ''))
    }
}
if ($failed -gt 0) {
    Write-Host "[build-ea] GAGAL: $failed dari $($results.Count) target tidak bersih (aturan: 0 error, 0 warning)."
    exit 1
}
Write-Host "[build-ea] OK: $($results.Count) target, 0 error, 0 warning."
exit 0

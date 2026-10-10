<#
.SYNOPSIS
    Replay tester periode live per simbol (spec 29, Fase 6).

.DESCRIPTION
    Untuk setiap simbol: ambil input sesi live (live_compare.py inputs), lalu jalankan
    run-ea-tests.ps1 -Baseline -Symbols <SYM> -FromDate -ToDate -Model 4 -SetInput <input live>.
    Di akhir mencetak rentang sesi tester (replay=A-B) untuk `live_compare.py compare --replay A-B`.
    Menolak jalan bila terminal tester sedang hidup (sesi lain memakai tester; batas CPU satu agen).

.PARAMETER From
    Tanggal UTC yyyy-MM-dd (inklusif).
.PARAMETER To
    Tanggal UTC yyyy-MM-dd (eksklusif).
.PARAMETER Symbols
    Default: 12 simbol dari ea\tests\baseline\BL-*.ini.
.PARAMETER Version
    Hanya sesi live dengan ea_version ini (misalnya 1.25).
.PARAMETER ExportCalendar
    Ekspor CSV kalender di terminal uji sebelum replay (filter berita).
.PARAMETER DryRun
    Hanya mencetak perintah; tidak menjalankan tester.
#>
param(
    [Parameter(Mandatory = $true)][string]$From,
    [Parameter(Mandatory = $true)][string]$To,
    [string[]]$Symbols = @(),
    [string]$Version = '',
    [switch]$ExportCalendar,
    [switch]$DryRun,
    [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
$sdbot = Split-Path $tools -Parent
$repo = Split-Path $sdbot -Parent
if (-not $Config) { $Config = Join-Path $tools 'mt5-paths.local.json' }
$cfg = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$testerDb = Join-Path $cfg.commonFilesDir 'sdbot_tester.sqlite'

function Write-Replay([string]$msg) { Write-Host "[live-replay] $msg" }

function Get-MaxSession {
    if (-not (Test-Path -LiteralPath $testerDb)) { return 0 }
    $py = "import sqlite3,sys; c=sqlite3.connect(r'file:${testerDb}?mode=ro', uri=True); print(c.execute('SELECT COALESCE(MAX(id),0) FROM sessions').fetchone()[0])"
    return [int](& uv run --project $repo python -c $py)
}

if (-not $Symbols -or $Symbols.Count -eq 0) {
    $Symbols = Get-ChildItem -Path (Join-Path $sdbot 'ea\tests\baseline') -Filter 'BL-*.ini' |
        ForEach-Object { $_.BaseName.Substring(3) } | Sort-Object
}
$fromTs = [datetime]::ParseExact($From, 'yyyy-MM-dd', $null)
$toTs = [datetime]::ParseExact($To, 'yyyy-MM-dd', $null)
if ($fromTs -ge $toTs) { Write-Replay '-From harus sebelum -To'; exit 2 }

if (-not $DryRun) {
    $busy = Get-Process -Name terminal64, metatester64 -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -ieq $cfg.testTerminal -or $_.Name -eq 'metatester64' }
    if ($busy) {
        Write-Replay 'terminal tester sedang hidup (dipakai sesi lain?); replay tidak dijalankan'
        exit 4
    }
}

$runner = Join-Path $tools 'run-ea-tests.ps1'
$compare = Join-Path $tools 'live_compare.py'
$before = if ($DryRun) { 0 } else { Get-MaxSession }
$failed = @()
$first = $true
foreach ($sym in $Symbols) {
    $pyArgs = @('inputs', $sym, '--from', $From, '--to', $To)
    if ($Version) { $pyArgs += @('--version', $Version) }
    $lines = & uv run --project $repo python $compare @pyArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Replay "$sym dilewati: $($lines -join ' ')"
        $failed += $sym
        continue
    }
    $setInput = @($lines | Where-Object { $_ -match '=' })
    # Splatting hashtable: splatting array mengirim '-Baseline' dsb. sebagai argumen posisi, bukan nama parameter.
    $runArgs = @{
        Baseline  = $true
        SkipBuild = $true
        Symbols   = @($sym)
        FromDate  = $fromTs.ToString('yyyy.MM.dd')
        ToDate    = $toTs.ToString('yyyy.MM.dd')
        Model     = 4
        SetInput  = $setInput
    }
    if ($ExportCalendar -and $first) { $runArgs['ExportCalendar'] = $true }
    $first = $false
    if ($DryRun) {
        $shown = ($runArgs.Keys | Where-Object { $_ -ne 'SetInput' } | Sort-Object | ForEach-Object { "-$_ $($runArgs[$_])" }) -join ' '
        Write-Replay ("{0}: run-ea-tests.ps1 {1} -SetInput ({2} kunci): {3}" -f $sym, $shown, $setInput.Count,
            (($setInput | Select-Object -First 4) -join ', '))
        continue
    }
    Write-Replay "$sym mulai ($($setInput.Count) input live)"
    # Dipanggil di proses yang sama agar array -SetInput tidak dipecah ulang oleh powershell -File.
    $pre = Get-MaxSession
    & $runner @runArgs
    # Kode 1 dari runner biasanya kriteria jumlah trade baseline-report (tidak berlaku untuk replay pendek);
    # replay dianggap jalan bila sesi tester baru terbentuk.
    if ((Get-MaxSession) -le $pre) { $failed += $sym; Write-Replay "$sym gagal: tidak ada sesi tester baru (kode $LASTEXITCODE)" }
    elseif ($LASTEXITCODE -ne 0) { Write-Replay "$sym selesai (kriteria baseline-report diabaikan untuk replay)" }
}

if ($DryRun) { Write-Replay "dry run: $($Symbols.Count) simbol, dilewati: $($failed -join ', ')"; exit 0 }
$after = Get-MaxSession
if ($after -gt $before) { Write-Replay ("replay={0}-{1}" -f ($before + 1), $after) } else { Write-Replay 'tidak ada sesi replay baru' }
if ($failed) { Write-Replay "gagal/dilewati: $($failed -join ', ')"; exit 1 }
exit 0

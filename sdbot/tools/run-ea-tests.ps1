<#
.SYNOPSIS
    Compile lalu jalankan unit test dan/atau skenario SDBot di Strategy Tester terminal uji.

.DESCRIPTION
    Unit test: EA SDBotTests\RunUnitTestsEA menjalankan semua suite di OnInit dan menulis
    Common\Files\sdbot_test_<runId>.txt. Skenario: harness dengan konfigurasi dari
    ea\tests\scenarios\<ID>_*.ini (+ .set bernama sama), dipakai mulai spec 04.

    Runner tidak pernah melaporkan lulus palsu: file hasil wajib ada, wajib berisi baris END
    untuk runId ini, dan jumlah test wajib > 0.

    Kode keluar: 0 = semua lulus, 1 = ada yang gagal (atau compile gagal),
    2 = lingkungan belum siap, 3 = melewati batas waktu.

.PARAMETER Unit
    Jalankan unit test (default bila tidak ada parameter lain).
.PARAMETER Scenario
    Jalankan satu atau beberapa skenario, misalnya -Scenario SC-00,SC-06.
.PARAMETER All
    Unit test lalu semua skenario di ea\tests\scenarios.
.PARAMETER SkipBuild
    Lewati compile.
.PARAMETER TimeoutSec
    Ganti batas waktu per run (default dari mt5-paths.local.json).
.PARAMETER Config
    Path mt5-paths.local.json (default sdbot\tools\mt5-paths.local.json).
#>
param(
    [switch]$Unit,
    [string[]]$Scenario = @(),
    [switch]$All,
    [switch]$SkipBuild,
    [int]$TimeoutSec = 0,
    [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'lib\Mt5Paths.psm1') -Force

function Write-Run([string]$msg) { Write-Host "[run-ea-tests] $msg" }

# ------------------------------------------------------------------ helper

function Get-TestTerminalProcesses {
    # Terminal uji dan agen tester lokalnya (metatester64) di folder instalasi yang sama.
    Get-Process -Name terminal64, metatester64 -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($script:terminalDir, [StringComparison]::OrdinalIgnoreCase) }
}

function Get-TerminalLogReasons([datetime]$since) {
    # Saat file hasil tidak ada, alasan kegagalan tester ada di log terminal (UTF-16, kolom tab:
    # kode, level, waktu, sumber, pesan). Ambil baris Tester/Terminal sejak run dimulai.
    $log = Join-Path $script:cfg.TestDataDir ("logs\{0}.log" -f $since.ToString('yyyyMMdd'))
    if (-not (Test-Path -LiteralPath $log)) { return @("(log terminal tidak ada: $log)") }
    $from = $since.TimeOfDay.Subtract([TimeSpan]::FromSeconds(1))
    $out = @()
    foreach ($line in (Get-Content -LiteralPath $log -Encoding Unicode)) {
        $cols = $line -split "`t"
        if ($cols.Count -lt 5) { continue }
        $t = [TimeSpan]::Zero
        if (-not [TimeSpan]::TryParse($cols[2], [ref]$t) -or $t -lt $from) { continue }
        if ($cols[3] -in @('Tester', 'Terminal') -or $cols[4] -match 'history|symbol|tester|shutdown') {
            $out += ("{0}: {1}" -f $cols[3], ($cols[4..($cols.Count - 1)] -join ' '))
        }
    }
    if ($out.Count -eq 0) { $out = @("(tidak ada baris Tester/Terminal di $log sejak $($since.ToString('HH:mm:ss')))") }
    return $out
}

function Get-AgentLogTail([int]$count) {
    # Jurnal tester di folder data terminal memuat output EA uji per agen ("Core 01 ...").
    $log = Get-ChildItem -Path (Join-Path $script:cfg.TestDataDir 'Tester\logs') -Filter '*.log' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1
    if ($null -eq $log) { return @('(jurnal tester tidak ditemukan)') }
    return @(Get-Content -LiteralPath $log.FullName -Encoding Unicode -Tail $count | ForEach-Object {
            $c = $_ -split "`t"; if ($c.Count -ge 5) { "{0} {1}: {2}" -f $c[2], $c[3], ($c[4..($c.Count - 1)] -join ' ') } else { $_ } })
}

function New-RunId([string]$prefix) {
    $rand = -join ((48..57) + (97..122) | Get-Random -Count 4 | ForEach-Object { [char]$_ })
    return ('{0}-{1}-{2}' -f $prefix, (Get-Date -Format 'yyyyMMdd-HHmmss'), $rand)
}

function Read-ScenarioIni([string]$path) {
    # File skenario di repo ditulis UTF-8: baris key=value, [section] dan komentar ; # diabaikan.
    $keys = [ordered]@{}
    foreach ($line in (Get-Content -LiteralPath $path -Encoding UTF8)) {
        $l = $line.Trim()
        if ($l -eq '' -or $l.StartsWith(';') -or $l.StartsWith('#') -or $l.StartsWith('[')) { continue }
        $i = $l.IndexOf('=')
        if ($i -gt 0) { $keys[$l.Substring(0, $i).Trim()] = $l.Substring($i + 1).Trim() }
    }
    return $keys
}

function Get-DbStamp([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return 'tidak ada' }
    $f = Get-Item -LiteralPath $path
    return '{0} byte, {1:o}' -f $f.Length, $f.LastWriteTimeUtc
}

# Optimasi (spec 07 SC-09): pass berjalan di agen tester, jadi yang diperiksa runner adalah laporan
# optimasi dan file DB tester, bukan file hasil harness. Kode kembali sama dengan skenario biasa.
function Test-OptimizationRun($r, [string]$reportBase, [string]$dbPath, [string]$dbBefore, [int]$secs) {
    $checks = @()
    $dbAfter = Get-DbStamp $dbPath
    $checks += [pscustomobject]@{ Id = "$($r.Id)-db"; Ok = ($dbAfter -eq $dbBefore); Text = "file DB tester tidak berubah (sebelum: $dbBefore; sesudah: $dbAfter)" }
    $report = @('.xml', '.htm', '.html') | ForEach-Object { "$reportBase$_" } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $rows = @()
    if ($report) {
        $text = [IO.File]::ReadAllText($report)
        $rowMatches = [regex]::Matches($text, '(?s)<Row[^>]*>(.*?)</Row>')
        foreach ($m in $rowMatches) {
            $cells = @([regex]::Matches($m.Groups[1].Value, '(?s)<Data[^>]*>(.*?)</Data>') | ForEach-Object { $_.Groups[1].Value.Trim() })
            if ($cells.Count -gt 0) { $rows += , $cells }
        }
    }
    $checks += [pscustomobject]@{ Id = "$($r.Id)-report"; Ok = [bool]$report; Text = "laporan optimasi dibuat ($report)" }
    $resultIdx = if ($rows.Count -gt 0) { [array]::IndexOf($rows[0], 'Result') } else { -1 }
    $passes = @($rows | Select-Object -Skip 1)
    $numeric = @($passes | Where-Object { $resultIdx -ge 0 -and $_.Count -gt $resultIdx -and ($_[$resultIdx] -as [double]) -ne $null })
    $values = ($numeric | ForEach-Object { $_[$resultIdx] }) -join ', '
    $nonZero = @($numeric | Where-Object { [double]$_[$resultIdx] -ne 0 })
    $checks += [pscustomobject]@{ Id = "$($r.Id)-passes"; Ok = ($passes.Count -ge 2 -and $numeric.Count -eq $passes.Count); Text = "laporan berisi >= 2 pass dengan hasil custom terisi ($($passes.Count) pass; Result: $values)" }
    # Result 0 bisa berarti trade < 30 (aturan metrik); minimal satu pass harus membuktikan metrik benar-benar dihitung.
    $checks += [pscustomobject]@{ Id = "$($r.Id)-metric"; Ok = ($nonZero.Count -ge 1); Text = "minimal satu pass dengan metrik custom != 0 ($($nonZero.Count))" }
    if ($resultIdx -lt 0 -and $rows.Count -gt 0) { Write-Host ("    INFO header laporan: " + ($rows[0] -join ' | ')) }
    $fail = 0
    $lines = @()
    foreach ($c in $checks) {
        $line = $(if ($c.Ok) { "PASS $($c.Id) $($c.Text)" } else { $fail++; "FAIL $($c.Id) $($c.Text)" })
        $lines += $line
        if (-not $c.Ok) { Write-Host "    $line" }
    }
    Set-Content -LiteralPath (Join-Path $script:tmp "last-$($r.Id).txt") -Value $lines -Encoding UTF8
    if ($report) { Copy-Item -LiteralPath $report -Destination (Join-Path $script:tmp ("last-$($r.Id)-report" + [IO.Path]::GetExtension($report))) -Force; Remove-Item -LiteralPath $report -Force }
    Write-Run ("{0} {1}: pass={2} fail={3} ({4} detik, optimasi)" -f $(if ($fail -eq 0) { 'LULUS' } else { 'GAGAL' }), $r.Id, ($checks.Count - $fail), $fail, $secs)
    if ($fail -gt 0) { return 1 }
    return 0
}

function Invoke-TesterRun($r) {
    $runId = New-RunId $r.Id
    $resultFile = Join-Path $script:cfg.CommonFilesDir "sdbot_test_$runId.txt"
    if (Test-Path -LiteralPath $resultFile) { Remove-Item -LiteralPath $resultFile -Force }

    if (-not (Test-Path -LiteralPath $script:testerProfiles)) { New-Item -ItemType Directory -Path $script:testerProfiles | Out-Null }
    $setPath = Join-Path $script:testerProfiles "$runId.set"
    $iniPath = Join-Path $script:tmp "$runId.ini"

    # Run unit mulai di bar pertama; Sabtu/Minggu/Senin 00:00 pasar tutup sehingga
    # suite yang membuka posisi gagal "market closed". Mundur ke Selasa..Jumat.
    $unitFrom = (Get-Date).AddDays(-7)
    while (@('Saturday', 'Sunday', 'Monday') -contains $unitFrom.DayOfWeek.ToString()) { $unitFrom = $unitFrom.AddDays(-1) }
    $tester = [ordered]@{
        Expert   = 'SDBotTests\RunUnitTestsEA.ex5'
        Symbol   = $script:cfg.TestSymbol
        Period   = 'M15'
        Model    = '2'
        FromDate = $unitFrom.ToString('yyyy.MM.dd')
        ToDate   = (Get-Date).ToString('yyyy.MM.dd')
    }
    $setLines = @()
    if ($r.Kind -eq 'scenario') {
        $tester['Expert'] = 'SDBotTests\SDBotHarness.ex5'
        $sc = Read-ScenarioIni $r.Ini
        foreach ($k in $sc.Keys) { $tester[$k] = $sc[$k] }
        if ($r.Set) {
            $setLines = @(Get-Content -LiteralPath $r.Set -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*InpTestRunId\s*=' })
        }
    }
    $isOpt = ($r.Kind -eq 'scenario') -and $tester.Contains('Optimization') -and ($tester['Optimization'] -ne '0')
    $reportBase = Join-Path $script:cfg.TestDataDir "sdbot_opt_$runId"
    $dbPath = Join-Path $script:cfg.CommonFilesDir 'sdbot_tester.sqlite'
    $dbBefore = Get-DbStamp $dbPath
    if ($isOpt) {
        $tester['Report'] = "sdbot_opt_$runId"   # relatif ke folder data terminal uji
        $tester['ReplaceReport'] = '1'
    }
    $tester['ExpertParameters'] = "$runId.set"
    $tester['ShutdownTerminal'] = '1'
    $setLines += "InpTestRunId=$runId"
    Set-Content -LiteralPath $setPath -Value $setLines -Encoding Unicode

    # [Experts] Enabled=0: EA di chart terminal uji (jika ada) tidak ikut jalan selama run.
    $ini = @('[Experts]', 'Enabled=0', 'AllowLiveTrading=0', 'AllowDllImport=0', '[Tester]')
    foreach ($k in $tester.Keys) { $ini += "$k=$($tester[$k])" }
    Set-Content -LiteralPath $iniPath -Value $ini -Encoding Unicode

    # Sandbox MQL5 tidak bisa membaca MQL5\Presets: preset disalin ke Common\Files untuk suite TestPresets (spec 07).
    $presetCopy = Join-Path $script:cfg.CommonFilesDir 'sdbot_presets'
    if ($r.Kind -eq 'unit') {
        if (Test-Path -LiteralPath $presetCopy) { Remove-Item -LiteralPath $presetCopy -Recurse -Force }
        New-Item -ItemType Directory -Path $presetCopy | Out-Null
        Get-ChildItem -LiteralPath (Join-Path $script:repoEa 'src\Presets') -Filter '*.set' -File |
            Where-Object { $_.Name -notlike '*.local.set' } |
            ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $presetCopy }
    }

    Write-Run ("mulai {0} (run {1}, {2} {3} {4}..{5}, batas {6} detik)" -f $r.Id, $runId, $tester['Symbol'], $tester['Period'], $tester['FromDate'], $tester['ToDate'], $script:timeoutSec)
    $start = Get-Date
    $timedOut = $false
    try {
        $p = Start-Process -FilePath $script:cfg.TestTerminal -ArgumentList "/config:`"$iniPath`"" -PassThru
        if (-not $p.WaitForExit($script:timeoutSec * 1000)) {
            $timedOut = $true
            Get-TestTerminalProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            $deadline = (Get-Date).AddSeconds(30)
            while ((Get-TestTerminalProcesses) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
        }
    }
    finally {
        Remove-Item -LiteralPath $setPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $iniPath -Force -ErrorAction SilentlyContinue
        if ($r.Kind -eq 'unit') { Remove-Item -LiteralPath $presetCopy -Recurse -Force -ErrorAction SilentlyContinue }
    }
    $secs = [int]((Get-Date) - $start).TotalSeconds

    if ($timedOut) {
        # EA uji bisa sempat menulis sebagian hasil sebelum dihentikan; jangan biarkan tertinggal.
        Remove-Item -LiteralPath $resultFile -Force -ErrorAction SilentlyContinue
        $left = @(Get-TestTerminalProcesses).Count
        Write-Run "TIMEOUT $($r.Id) setelah $($script:timeoutSec) detik; proses terminal uji tersisa: $left"
        return 3
    }
    if ($isOpt) {
        Remove-Item -LiteralPath $resultFile -Force -ErrorAction SilentlyContinue
        return Test-OptimizationRun $r $reportBase $dbPath $dbBefore $secs
    }
    if (-not (Test-Path -LiteralPath $resultFile)) {
        Write-Run "GAGAL $($r.Id): file hasil tidak dibuat ($secs detik). Dari log terminal:"
        Get-TerminalLogReasons $start | ForEach-Object { Write-Host "    $_" }
        return 1
    }

    $lines = @(Get-Content -LiteralPath $resultFile)
    Copy-Item -LiteralPath $resultFile -Destination (Join-Path $script:tmp "last-$($r.Id).txt") -Force
    Remove-Item -LiteralPath $resultFile -Force
    foreach ($l in $lines) {
        if ($l -match '^(FAIL|INFO|SUITE_END) ') { Write-Host "    $l" }
    }
    $end = $lines | Where-Object { $_ -match ('^RUN ' + [regex]::Escape($runId) + ' END pass=(\d+) fail=(\d+)') } | Select-Object -Last 1
    if (-not $end) {
        Write-Run "GAGAL $($r.Id): EA uji berhenti di tengah (tidak ada baris END). Log agen tester terakhir:"
        Get-AgentLogTail 20 | ForEach-Object { Write-Host "    $_" }
        return 1
    }
    [void]($end -match 'pass=(\d+) fail=(\d+)')
    $pass = [int]$Matches[1]; $fail = [int]$Matches[2]
    if ($pass + $fail -eq 0) {
        Write-Run "GAGAL $($r.Id): tidak ada test yang dijalankan."
        return 1
    }
    Write-Run ("{0} {1}: pass={2} fail={3} ({4} detik)" -f $(if ($fail -eq 0) { 'LULUS' } else { 'GAGAL' }), $r.Id, $pass, $fail, $secs)
    if ($fail -gt 0) { return 1 }
    return 0
}

function Invoke-Main {
    if (Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -ieq $script:cfg.TestTerminal }) {
        Write-Run "terminal uji sedang terbuka ($($script:cfg.TestTerminal)). Tutup dulu; runner tidak menutupnya sendiri."
        return 2
    }
    if ($SkipBuild) {
        # Tanpa build, .ex5 bisa basi (source sudah berubah) dan hasil uji menipu.
        # -Include tidak bisa dipercaya bersama -LiteralPath di PowerShell 5.1; filter ekstensi manual.
        $srcNewest = Get-ChildItem -LiteralPath $script:repoEa -Recurse -File |
            Where-Object { $_.Extension -in @('.mq5', '.mqh') } | Sort-Object LastWriteTime | Select-Object -Last 1
        $experts = @('tests\Experts\SDBotTests\RunUnitTestsEA.ex5')
        if ($script:runs | Where-Object { $_.Kind -eq 'scenario' }) { $experts += 'tests\Experts\SDBotTests\SDBotHarness.ex5' }
        foreach ($e in $experts) {
            $ex5 = Join-Path $script:repoEa $e
            if (-not (Test-Path -LiteralPath $ex5)) { Write-Run "'$e' belum di-build; jalankan tanpa -SkipBuild."; return 2 }
            if ($srcNewest -and $srcNewest.LastWriteTime -gt (Get-Item -LiteralPath $ex5).LastWriteTime) {
                Write-Run "'$e' lebih lama dari '$($srcNewest.Name)'; jalankan tanpa -SkipBuild."
                return 2
            }
        }
    }
    else {
        # Out-Host: output build tidak boleh ikut menjadi nilai kembalian fungsi ini.
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-ea.ps1') -Terminal test -Config $script:cfg.ConfigPath | Out-Host
        $b = $LASTEXITCODE
        if ($b -ne 0) {
            Write-Run 'build gagal, uji tidak dijalankan.'
            return $(if ($b -eq 2) { 2 } else { 1 })
        }
    }
    $summary = @()
    $allStart = Get-Date
    foreach ($r in $script:runs) {
        $code = Invoke-TesterRun $r
        $summary += [pscustomobject]@{ Run = $r.Id; Code = $code }
    }
    Write-Host ''
    Write-Run ("durasi total {0:mm\:ss} untuk {1} run" -f ((Get-Date) - $allStart), $summary.Count)
    foreach ($s in $summary) {
        $label = switch ($s.Code) { 0 { 'PASS' } 1 { 'FAIL' } 2 { 'ENV ' } 3 { 'TIME' } }
        Write-Run ("{0} {1}" -f $label, $s.Run)
    }
    if ($summary | Where-Object { $_.Code -eq 3 }) { return 3 }
    if ($summary | Where-Object { $_.Code -ne 0 }) { return 1 }
    return 0
}

# ------------------------------------------------------------------ persiapan

try { $script:cfg = Get-Mt5Config -Path $Config }
catch { Write-Run $_.Exception.Message; exit 2 }
$script:timeoutSec = $(if ($TimeoutSec -gt 0) { $TimeoutSec } else { $script:cfg.TimeoutSec })
$script:tmp = Join-Path $PSScriptRoot '.tmp'
if (-not (Test-Path -LiteralPath $script:tmp)) { New-Item -ItemType Directory -Path $script:tmp | Out-Null }
$script:testerProfiles = Join-Path $script:cfg.TestDataDir 'MQL5\Profiles\Tester'
$script:terminalDir = Split-Path -Parent $script:cfg.TestTerminal
$script:repoEa = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\ea'))
$repoEa = $script:repoEa

if (-not $Unit -and $Scenario.Count -eq 0 -and -not $All) { $Unit = $true }
$script:runs = @()
if ($Unit -or $All) { $script:runs += [pscustomobject]@{ Kind = 'unit'; Id = 'unit'; Ini = $null; Set = $null } }
$scenarioDir = Join-Path $repoEa 'tests\scenarios'
$wanted = @($Scenario | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
if ($All) {
    $wanted = @(Get-ChildItem -LiteralPath $scenarioDir -Filter 'SC-*.ini' -File -ErrorAction SilentlyContinue |
        ForEach-Object { ($_.BaseName -split '_')[0] } | Sort-Object -Unique)
}
foreach ($id in $wanted) {
    $ini = Get-ChildItem -LiteralPath $scenarioDir -Filter "$id`_*.ini" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $ini) { $ini = Get-ChildItem -LiteralPath $scenarioDir -Filter "$id.ini" -File -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if ($null -eq $ini) { Write-Run "skenario '$id' tidak ditemukan di $scenarioDir"; exit 2 }
    $set = [IO.Path]::ChangeExtension($ini.FullName, '.set')
    $script:runs += [pscustomobject]@{ Kind = 'scenario'; Id = $id; Ini = $ini.FullName; Set = $(if (Test-Path -LiteralPath $set) { $set } else { $null }) }
}

# ------------------------------------------------------------------ kunci + jalankan

$lock = Join-Path $script:tmp 'run.lock'
if (Test-Path -LiteralPath $lock) {
    $otherPid = 0
    [void][int]::TryParse(([string](Get-Content -LiteralPath $lock -Raw)).Trim(), [ref]$otherPid)
    if ($otherPid -gt 0 -and $otherPid -ne $PID -and (Get-Process -Id $otherPid -ErrorAction SilentlyContinue)) {
        Write-Run "runner lain sedang berjalan (PID $otherPid). Tunggu sampai selesai."
        exit 2
    }
    Write-Run "kunci basi dari PID $otherPid diabaikan."
}
Set-Content -LiteralPath $lock -Value $PID -Encoding ASCII
$exitCode = 2
try { $exitCode = Invoke-Main }
finally { Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue }
exit $exitCode

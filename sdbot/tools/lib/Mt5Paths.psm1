# Mt5Paths.psm1 - baca dan validasi sdbot\tools\mt5-paths.local.json.
# Semua kesalahan konfigurasi dilempar sebagai exception berawalan "CONFIG:" agar
# skrip pemanggil bisa keluar dengan kode 2 dan pesan yang menyebut kunci yang salah.

$script:RequiredPathKeys = @('metaeditor', 'testTerminal', 'testDataDir', 'liveDataDir', 'commonFilesDir')

function Get-DefaultMt5ConfigPath {
    return (Join-Path (Split-Path -Parent $PSScriptRoot) 'mt5-paths.local.json')
}

function Get-Mt5Config {
    param([string]$Path = '')
    if ([string]::IsNullOrEmpty($Path)) { $Path = Get-DefaultMt5ConfigPath }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "CONFIG: file '$Path' tidak ada. Salin sdbot\tools\mt5-paths.example.json menjadi mt5-paths.local.json lalu isi path mesin ini."
    }
    try {
        $cfg = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "CONFIG: '$Path' bukan JSON yang valid: $($_.Exception.Message). Backslash di path harus ditulis \\."
    }
    foreach ($k in $script:RequiredPathKeys) {
        $v = $cfg.$k
        if ([string]::IsNullOrWhiteSpace($v)) {
            throw "CONFIG: kunci '$k' kosong atau tidak ada di '$Path'."
        }
        if (-not (Test-Path -LiteralPath $v)) {
            throw "CONFIG: path untuk '$k' tidak ditemukan: '$v'."
        }
    }
    $test = [IO.Path]::GetFullPath($cfg.testDataDir).TrimEnd('\')
    $live = [IO.Path]::GetFullPath($cfg.liveDataDir).TrimEnd('\')
    if ($test -ieq $live) {
        throw "CONFIG: 'testDataDir' sama dengan 'liveDataDir' ($test). Terminal uji wajib terpisah dari terminal live."
    }
    if ([string]::IsNullOrWhiteSpace($cfg.testSymbol)) {
        throw "CONFIG: kunci 'testSymbol' kosong (contoh: EURUSDc)."
    }
    $timeout = 0
    if (-not [int]::TryParse([string]$cfg.timeoutSec, [ref]$timeout) -or $timeout -le 0) {
        throw "CONFIG: 'timeoutSec' harus bilangan bulat > 0 (sekarang: '$($cfg.timeoutSec)')."
    }
    return [pscustomobject]@{
        ConfigPath     = $Path
        MetaEditor     = $cfg.metaeditor
        TestTerminal   = $cfg.testTerminal
        TestDataDir    = $test
        LiveDataDir    = $live
        CommonFilesDir = $cfg.commonFilesDir
        TestSymbol     = $cfg.testSymbol
        TimeoutSec     = $timeout
    }
}

# Petakan file di repo (relatif ke sdbot\ea) ke path junction di folder data MT5.
function Convert-RepoPathToMt5 {
    param([Parameter(Mandatory = $true)][string]$RepoRelative, [Parameter(Mandatory = $true)][string]$DataDir)
    $map = [ordered]@{
        'src\Experts\SDBot\'        = 'MQL5\Experts\SDBot\'
        'src\Scripts\SDBot\'        = 'MQL5\Scripts\SDBot\'
        'tests\Experts\SDBotTests\' = 'MQL5\Experts\SDBotTests\'
        'tests\Scripts\SDBotTests\' = 'MQL5\Scripts\SDBotTests\'
    }
    $rel = $RepoRelative.Replace('/', '\').TrimStart('\')
    foreach ($prefix in $map.Keys) {
        if ($rel.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            return (Join-Path $DataDir ($map[$prefix] + $rel.Substring($prefix.Length)))
        }
    }
    return $null
}

Export-ModuleMember -Function Get-Mt5Config, Get-DefaultMt5ConfigPath, Convert-RepoPathToMt5

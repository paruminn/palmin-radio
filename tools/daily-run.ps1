param([switch]$Preview)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stateRoot = Join-Path $env:LOCALAPPDATA 'PalminRadio'
$logRoot = Join-Path $stateRoot 'logs'
$pythonPath = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
$ollamaPath = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$coeiroinkPath = Join-Path $env:USERPROFILE 'Downloads\COEIROINK_WIN_CPU_v.2.13.0\COEIROINK_WIN_CPU_v.2.13.0\COEIROINK_WIN_CPU_v.2.13.0\COEIROINKv2.exe'
$ffmpegPath = 'C:\Program Files (x86)\Steam\steamapps\common\Lethal Company\BoomboxController\other\ffmpeg.exe'
$bashPath = 'C:\Program Files\Git\bin\bash.exe'

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$logPath = Join-Path $logRoot (Get-Date -Format 'yyyy-MM-dd')
Start-Transcript -Path $logPath -Append | Out-Null
try {
    foreach ($requiredPath in @($pythonPath, $ollamaPath, $ffmpegPath, $bashPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required daily-run file is missing: $requiredPath"
        }
    }

    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 | Out-Null
    }
    catch {
        Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden
        $ready = $false
        for ($attempt = 0; $attempt -lt 24; $attempt++) {
            Start-Sleep -Seconds 5
            try {
                Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 | Out-Null
                $ready = $true
                break
            }
            catch {}
        }
        if (-not $ready) { throw 'Ollama did not become ready within two minutes.' }
    }

    $env:PALMIN_FFMPEG = $ffmpegPath
    $env:PALMIN_BASH = $bashPath
    $env:PYTHONUTF8 = '1'
    $env:PATH = "$(Split-Path $pythonPath);C:\Program Files\Git\cmd;$env:PATH"
    Set-Location -LiteralPath $repoRoot

    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:50032/v1/speakers' -TimeoutSec 5 | Out-Null
    }
    catch {
        if (-not (Test-Path -LiteralPath $coeiroinkPath -PathType Leaf)) {
            throw "COEIROINK is not running and the installed app was not found: $coeiroinkPath"
        }
        Start-Process -FilePath $coeiroinkPath -WindowStyle Hidden
        $ready = $false
        for ($attempt = 0; $attempt -lt 24; $attempt++) {
            Start-Sleep -Seconds 5
            try {
                Invoke-RestMethod -Uri 'http://127.0.0.1:50032/v1/speakers' -TimeoutSec 5 | Out-Null
                $ready = $true
                break
            }
            catch {}
        }
        if (-not $ready) { throw 'COEIROINK did not become ready within two minutes.' }
    }

    $dailyArgs = @()
    if ($Preview) { $dailyArgs += '--preview' }
    & $pythonPath (Join-Path $repoRoot 'tools\daily_episode.py') @dailyArgs
    if ($LASTEXITCODE -ne 0) { throw "Daily episode process exited with code $LASTEXITCODE." }
}
finally {
    Stop-Transcript | Out-Null
}

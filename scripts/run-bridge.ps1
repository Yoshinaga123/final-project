param(
  [string]$Engine,                                      # 将棋エンジン exe へのパス or グロブ（未指定なら .env/環境変数）
  [int]$Port = 8787,
  [string]$Token,
  [string]$LogDir = "logs/usi-bridge",
  [string]$PythonExe,                                   # 省略時は PATH 上の python
  [string]$BridgeScript,                                # 未指定なら vendor/.. を自動探索 or .env
  [int]$ReadyTimeoutSec = 20,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# Repo ルートと相対パス解決
$RepoRoot = Split-Path -Parent $PSScriptRoot
function Resolve-Abs([string]$p){ if([string]::IsNullOrWhiteSpace($p)){ return $p } if([IO.Path]::IsPathRooted($p)){ return $p } return (Join-Path $RepoRoot $p) }

# .env 読み込み（単純な KEY=VALUE 形式）
$DotEnvPath = Join-Path $RepoRoot '.env'
if(Test-Path $DotEnvPath){
  try{
    Get-Content $DotEnvPath | ForEach-Object {
      $line = $_.Trim()
      if($line -eq '' -or $line.StartsWith('#')){ return }
      $kv = $line -split '=',2
      if($kv.Count -eq 2){
        $k = $kv[0].Trim(); $v = $kv[1].Trim().Trim('"').Trim("'")
        if(-not [string]::IsNullOrWhiteSpace($k)){
          if(-not (Get-Item "env:$k" -ErrorAction SilentlyContinue)){
            Set-Item "env:$k" $v
          }
        }
      }
    }
  } catch { Write-Warning "Failed to parse .env: $DotEnvPath ($_)" }
}

function Resolve-Engine([string]$pattern){
  if(Test-Path $pattern){ return (Resolve-Path $pattern).Path }
  $dir = Split-Path $pattern -Parent
  $name = Split-Path $pattern -Leaf
  $files = Get-ChildItem -Path $dir -Filter $name -File | Sort-Object LastWriteTime -Descending
  if($files.Count -eq 0){ throw "ENGINE_START_FAILED: engine not found: $pattern" }
  return $files[0].FullName
}

function Test-PortFree([int]$p){
  $inUse = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  return -not $inUse
}

function Ensure-LogDir([string]$path){ if(-not (Test-Path $path)){ New-Item -ItemType Directory -Path $path | Out-Null } }

# 環境変数のフォールバック
if(-not $PSBoundParameters.ContainsKey('Port') -and $env:USI_BRIDGE_PORT){ $Port = [int]$env:USI_BRIDGE_PORT }
if(-not $Token -and $env:USI_BRIDGE_TOKEN){ $Token = $env:USI_BRIDGE_TOKEN }

$Engine = if($Engine){ $Engine } elseif($env:USI_ENGINE_PATH){ $env:USI_ENGINE_PATH } else { $null }

# 本番ではフォールバックを禁止（設定漏れを隠さない）
if($env:APP_ENV -eq 'production' -and -not $Engine){
  throw "ENGINE_REQUIRED_IN_PROD: set -Engine or USI_ENGINE_PATH"
}

# Engine 決定（必須）: 未指定時はモックにフォールバック（開発/CIの利便性向上）
if(-not $Engine){
  $mock = Resolve-Abs "tools\mock_engine\mock_engine.bat"
  if(Test-Path $mock){
    Write-Warning "USI_ENGINE_PATH not set and -Engine not provided; using mock engine: $mock"
    $Engine = $mock
  } else {
    throw "MOCK_ENGINE_MISSING: $mock"
  }
}
$enginePath = Resolve-Engine (Resolve-Abs $Engine)

# -Port 0 を許容して自動割当
if($Port -eq 0){
  for($p=8800; $p -le 8899; $p++){
    $inUse = (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue)
    if(-not $inUse){ $Port = $p; break }
  }
}
if(-not (Test-PortFree $Port)){ throw "PORT_IN_USE: 127.0.0.1:$Port is already in use." }

$LogDir = Resolve-Abs $LogDir
Ensure-LogDir $LogDir
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $LogDir "bridge-$ts.log"

# Python 実行ファイルの解決: 明示指定 > final-project の .venv > PATH（prototype venv 依存は避ける）
if($PythonExe){
  $python = $PythonExe
} else {
  $projVenvPy  = Resolve-Abs ".venv\Scripts\python.exe"
  if(Test-Path $projVenvPy){ $python = $projVenvPy }
  else { $python = 'python' }
}

# BridgeScript 推定（final-project/tools のみ）
if(-not $BridgeScript){
  $cand0 = Resolve-Abs "tools/usi-bridge.py"
  $candEnv = $env:USI_BRIDGE_SCRIPT
  if($candEnv){ $candEnv = Resolve-Abs $candEnv }
  if(Test-Path $cand0){ $BridgeScript = $cand0 }
  elseif($candEnv -and (Test-Path $candEnv)){ $BridgeScript = $candEnv }
  else { throw "BRIDGE_SCRIPT_NOT_FOUND: place tools/usi-bridge.py or specify -BridgeScript / USI_BRIDGE_SCRIPT" }
} else {
  $BridgeScript = Resolve-Abs $BridgeScript
}

# Assemble args: adjust for your bridge CLI if different
$argList = @($BridgeScript, $enginePath)

# Port 指定: 0 の場合はスクリプト側で空きポートを選び、--auto も渡しておく
if($Port -eq 0){
  for($p=8800; $p -le 8899; $p++){
    $inUse = (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue)
    if(-not $inUse){ $Port = $p; break }
  }
  if(-not $Port){ $Port = 0 }
}

$argList += @($Port)
if($Token){ $argList += @('--token', $Token) }
# 自動ポートスキャンをブリッジ側にも許可
$useAuto = $true
if($env:USI_AUTO_PORT){ if($env:USI_AUTO_PORT -in @('0','false','False')){ $useAuto = $false } }
if($useAuto){ $argList += @('--auto') }

# ブリッジに実ポートのメタ書き出しをさせる（保険）。LogDir に last_port.txt を置かせる
$env:USI_PORT_DIR = (Resolve-Abs $LogDir)

Write-Host "Starting USI bridge..." -ForegroundColor Cyan
Write-Host "Engine: $enginePath"
Write-Host "Port:   $Port"
Write-Host "Log:    $log"
Write-Host "Cmd:    $python $($argList -join ' ')"

# 選定ポートをメタファイルに書き出し（UI側が自動検出に利用）
try {
  $lastPortFile = Join-Path $LogDir 'last_port.txt'
  Set-Content -Path $lastPortFile -Value $Port -Encoding ascii -Force
} catch { Write-Warning "failed to write last_port.txt: $_" }

# CIや親プロセスが拾いやすいよう案内も標準出力に出す
Write-Host "BRIDGE_PORT=$Port"

# 使ったポートを環境変数へエクスポート（下流プロセス用）
$env:USI_BRIDGE_PORT = $Port

if($DryRun){ exit 0 }


# 標準出力は $log、標準エラーは ${log}.err に分離（Window 隠し・ワーキングディレクトリはプロジェクトルート）
$proc = Start-Process -FilePath $python -ArgumentList $argList -RedirectStandardOutput $log -RedirectStandardError "${log}.err" -PassThru -WindowStyle Hidden -WorkingDirectory $RepoRoot

# Health check by tailing log for 'usiok' and 'readyok'
$deadline = (Get-Date).AddSeconds($ReadyTimeoutSec)
$ready = $false
while((Get-Date) -lt $deadline){
  Start-Sleep -Milliseconds 300
  $content = ''
  if(Test-Path $log){
    $content += (Get-Content $log -Tail 200 -ErrorAction SilentlyContinue | Out-String)
  }
  $logErr = "${log}.err"
  if(Test-Path $logErr){
    $content += (Get-Content $logErr -Tail 200 -ErrorAction SilentlyContinue | Out-String)
  }
  if($content -and $content -match 'usiok' -and $content -match 'readyok'){ $ready = $true; break }
  if($proc.HasExited){ throw "BRIDGE_EXITED_EARLY: exit $($proc.ExitCode). Check log: $log" }
}

if(-not $ready){ throw "BRIDGE_NOT_READY: didn't see 'usiok/readyok' within ${ReadyTimeoutSec}s. Check log: $log" }

Write-Host "USI bridge is READY (usiok/readyok detected)." -ForegroundColor Green
Write-Host "Follow logs: Get-Content -Path \"$log\" -Wait"

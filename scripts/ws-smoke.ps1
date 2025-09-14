param(
  [string]$WsHost = $env:USI_BRIDGE_HOST,
  [int]$Port = [int]($env:USI_BRIDGE_PORT),
  [string]$PythonExe
)

# 目的:
# - tools/ws_smoke.py を簡単に実行し、WSブリッジのE2Eスモークを流す
# - Host/Port は未指定なら last_port.txt / 既定にフォールバック（ws_smoke.py 自身が対応）

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$script = Join-Path $RepoRoot 'tools/ws_smoke.py'
if(-not (Test-Path $script)) { throw "ws_smoke.py not found: $script" }

# Python 解決: 明示 > .venv > PATH
if($PythonExe){
  $python = $PythonExe
} else {
  $projVenvPy  = Join-Path $RepoRoot '.venv/Scripts/python.exe'
  if(Test-Path $projVenvPy){ $python = $projVenvPy } else { $python = 'python' }
}

# USI_BRIDGE_HOST/PORT を環境へエクスポート（指定があれば上書き）
if($WsHost){ $env:USI_BRIDGE_HOST = $WsHost }
if($Port){ $env:USI_BRIDGE_PORT = $Port }

Write-Host "Running ws_smoke: $python $script" -ForegroundColor Cyan
& $python $script

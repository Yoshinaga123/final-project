param(
  [string]$Engine,
  [int]$Port = 0,
  [switch]$UseMock
)

$ErrorActionPreference = 'Stop'
Write-Host "=== Shogi Engine Integration Test (final-project venv) ===" -ForegroundColor Green

# 1) venv を優先的に有効化（final-project/.venv）
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot ".venv/Scripts/Activate.ps1"
if(Test-Path $Venv){
  Write-Host "1) Activating venv: $Venv" -ForegroundColor Yellow
  & $Venv
} else {
  Write-Host "1) No local venv; using system python" -ForegroundColor Yellow
}

# 2) エンジンパスの決定（モック or 引数 or 環境変数）
if($UseMock){
  $Engine = Join-Path $RepoRoot "tools/mock_engine/mock_engine.bat"
}
if(-not $Engine){ $Engine = $env:USI_ENGINE_PATH }
if(-not $Engine){ throw "ENGINE_PARAM_REQUIRED: specify -Engine or -UseMock or set USI_ENGINE_PATH" }
Write-Host "Engine: $Engine" -ForegroundColor Cyan

# 3) USIブリッジ起動（Port=0 で自動割当）。READY になるまで待機
Write-Host "2) Starting USI bridge..." -ForegroundColor Yellow
& (Join-Path $RepoRoot 'scripts/run-bridge.ps1') -Engine $Engine -Port $Port

# 4) WS スモークテスト
Write-Host "3) Running WS smoke..." -ForegroundColor Yellow
& (Join-Path $RepoRoot 'scripts/ws-smoke.ps1')

Write-Host "=== Test Complete ===" -ForegroundColor Green

# Minimal setup helper for YaneuraOu on Windows
param(
  [string]$EngineRoot = 'C:\shogi\engines\yaneuraou',
  [string]$EvalRoot = 'C:\shogi\eval\suisho',
  [switch]$PersistEnv
)

Write-Host '=== Setup YaneuraOu (minimal) ===' -ForegroundColor Cyan

# 1) Create dirs
New-Item -ItemType Directory -Force -Path $EngineRoot | Out-Null
New-Item -ItemType Directory -Force -Path $EvalRoot   | Out-Null
Write-Host "Dirs ready: Engine=$EngineRoot Eval=$EvalRoot" -ForegroundColor Green

# 2) Guidance
Write-Host 'Next:' -ForegroundColor Yellow
Write-Host '  - Download from https://github.com/yaneurao/YaneuraOu/releases' -ForegroundColor White
Write-Host "  - Extract binaries under: $EngineRoot" -ForegroundColor White
Write-Host '  - Choose CPU-optimized exe (bmi2/avx2/sse41/sse2)' -ForegroundColor White

# 3) Auto-detect engine exe if placed
$candidates = 'YaneuraOu-bmi2.exe','YaneuraOu-avx2.exe','YaneuraOu-sse41.exe','YaneuraOu-sse2.exe','YaneuraOu.exe'
$enginePath = $null
foreach($c in $candidates){ $p = Join-Path $EngineRoot $c; if(Test-Path $p){ $enginePath = $p; break } }

if($enginePath){
  $env:ENGINE_PATH = $enginePath
  Write-Host "ENGINE_PATH = $env:ENGINE_PATH" -ForegroundColor Green
  if($PersistEnv){ setx ENGINE_PATH $enginePath | Out-Null }
} else {
  Write-Host 'Engine exe not found yet. Set ENGINE_PATH after placing files.' -ForegroundColor Yellow
}

# 4) Optional eval dir env
if(Test-Path $EvalRoot){
  $env:EVAL_DIR = $EvalRoot
  Write-Host "EVAL_DIR = $env:EVAL_DIR" -ForegroundColor Green
  if($PersistEnv){ setx EVAL_DIR $EvalRoot | Out-Null }
}

Write-Host 'Done. Tip: use scripts/run-bridge.ps1 -Engine <exe> -Port 0' -ForegroundColor Cyan

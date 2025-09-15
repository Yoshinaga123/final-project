param(
  [string]$Manifest = "tools/suisho_manifest.json",  # URL と SHA256 を定義した JSON（sample を参考に作成）
  [string]$InstallDir = "engines/suisho",            # 展開先（プロジェクト相対 or 絶対）
  [switch]$Force,                                      # 既存があっても上書き
  [switch]$NoEnv                                       # .env へUSI_ENGINE_PATHを書かない
)

$ErrorActionPreference = 'Stop'

function Resolve-Abs([string]$p){ if([string]::IsNullOrWhiteSpace($p)){ return $p } $root = Split-Path -Parent $PSScriptRoot; if([IO.Path]::IsPathRooted($p)){ return $p } return (Join-Path $root $p) }

$Manifest = Resolve-Abs $Manifest
$InstallDir = Resolve-Abs $InstallDir
$RepoRoot = Split-Path -Parent $PSScriptRoot

if(-not (Test-Path $Manifest)){
  Write-Host "Manifest not found: $Manifest" -ForegroundColor Red
  Write-Host "Create one based on: tools/suisho_manifest.sample.json" -ForegroundColor Yellow
  exit 2
}

# 読み込み
try{ $m = Get-Content $Manifest -Raw | ConvertFrom-Json } catch { Write-Host "Invalid manifest JSON: $_" -ForegroundColor Red; exit 2 }
if(-not $m.archiveUrl){ Write-Host "Manifest must include 'archiveUrl'" -ForegroundColor Red; exit 2 }

# GitHub blob → raw 変換（blob URL が来ても使えるように）
if($m.archiveUrl -match '^https://github\.com/.*/blob/'){
  # https://github.com/{owner}/{repo}/blob/{branch}/{path}
  $m.archiveUrl = $m.archiveUrl -replace '^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)$','https://raw.githubusercontent.com/$1/$2/$3/$4'
  Write-Host "Normalized to RAW URL: $($m.archiveUrl)" -ForegroundColor DarkCyan
}

# ダウンロード
$dlDir = Join-Path $RepoRoot "downloads"
if(-not (Test-Path $dlDir)){ New-Item -ItemType Directory -Path $dlDir | Out-Null }
$filename = Split-Path $m.archiveUrl -Leaf
$dst = Join-Path $dlDir $filename
Write-Host "Downloading: $($m.archiveUrl)" -ForegroundColor Cyan
Invoke-WebRequest -Uri $m.archiveUrl -OutFile $dst -UseBasicParsing

# ハッシュ検証（archiveSha256 が 'AUTO' または未指定なら計算のみ表示）
try{
  $sha = (Get-FileHash -Algorithm SHA256 $dst).Hash.ToLower()
  if($m.PSObject.Properties.Name -contains 'archiveSha256' -and $m.archiveSha256){
    if($m.archiveSha256.ToUpper() -eq 'AUTO'){
      Write-Host "SHA256 computed (AUTO mode): $sha" -ForegroundColor Yellow
    } else {
      if($sha -ne $m.archiveSha256.ToLower()){
        Write-Host "SHA256 mismatch!" -ForegroundColor Red
        Write-Host " expected: $($m.archiveSha256)" -ForegroundColor Yellow
        Write-Host " actual:   $sha" -ForegroundColor Yellow
        exit 3
      }
      Write-Host "SHA256 OK: $sha" -ForegroundColor Green
    }
  } else {
    Write-Host "SHA256 computed: $sha (no manifest value to verify)" -ForegroundColor Yellow
  }
} catch { Write-Host "Hash check failed: $_" -ForegroundColor Red; exit 3 }

# 展開
if(Test-Path $InstallDir){ if($Force){ Remove-Item -Recurse -Force $InstallDir } else { Write-Host "InstallDir exists: $InstallDir (use -Force to overwrite)" -ForegroundColor Yellow } }
if(-not (Test-Path $InstallDir)){ New-Item -ItemType Directory -Path $InstallDir | Out-Null }

$ext = [IO.Path]::GetExtension($dst).ToLower()
Write-Host "Extracting to: $InstallDir" -ForegroundColor Cyan
if($ext -eq ".exe"){
  # 直接 exe の配布に対応
  $exeName = if($m.engineRename){ $m.engineRename } else { Split-Path $dst -Leaf }
  $target = Join-Path $InstallDir $exeName
  Copy-Item -Force $dst $target
  $exe = $target
}
elseif($ext -eq ".zip"){
  Expand-Archive -Force -Path $dst -DestinationPath $InstallDir
} elseif($ext -eq ".7z" -or $ext -eq ".7zip" -or $filename.ToLower().EndsWith('.7z')){
  # 7zip が必要（choco install などで導入を案内）
  $seven = "7z"  # PATH 上の 7z.exe を想定
  try { & $seven x -y -o"$InstallDir" "$dst" } catch { Write-Host "7z not found. Install 7zip and ensure '7z' is in PATH." -ForegroundColor Red; exit 4 }
} else {
  Write-Host "Unknown archive type: $filename" -ForegroundColor Red; exit 4
}

# エンジン exe の決定
if(-not $exe){
  $exe = $null
  $hints = if($m.innerPathHints){ $m.innerPathHints } else { @("*.exe") }
  foreach($pt in $hints){
    $found = Get-ChildItem -Path $InstallDir -Filter $pt -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if($found -and $found.Count -gt 0){ $exe = $found[0].FullName; break }
  }
  if(-not $exe){ Write-Host "No engine .exe found under $InstallDir" -ForegroundColor Red; exit 5 }
  # 任意のリネーム
  if($m.engineRename){
    $target = Join-Path $InstallDir $m.engineRename
    try { Copy-Item -Force $exe $target } catch { $target = $exe }
    $exe = $target
  }
}
Write-Host "Engine detected: $exe" -ForegroundColor Green

# .env に USI_ENGINE_PATH を書き込む
if(-not $NoEnv){
  $envPath = Join-Path $RepoRoot ".env"
  if(-not (Test-Path $envPath)){ New-Item -ItemType File -Path $envPath | Out-Null }
  $lines = Get-Content $envPath -ErrorAction SilentlyContinue
  $key = "USI_ENGINE_PATH"
  $value = $exe
  $updated = $false
  $out = @()
  foreach($ln in $lines){
    if($ln -match "^$key="){
      $out += "$key=$value"; $updated = $true
    } else { $out += $ln }
  }
  if(-not $updated){ $out += "$key=$value" }
  Set-Content -Path $envPath -Value $out -Encoding UTF8 -Force
  Write-Host ".env updated: USI_ENGINE_PATH=$value" -ForegroundColor Cyan
}

Write-Host "Suisho setup complete." -ForegroundColor Green
Write-Host "Try: scripts\\run-bridge.ps1 -Port 8787" -ForegroundColor Yellow

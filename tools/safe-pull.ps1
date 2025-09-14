# 安全な pull 実行スクリプト
param(
  [string]$Remote = "origin",
  [string]$Branch = "main"
)

git rev-parse --is-inside-work-tree | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Not a git repo" }

$status = git status --porcelain
$hasChanges = -not [string]::IsNullOrWhiteSpace($status)
$stashed = $false
if ($hasChanges) {
  git stash push -u -m "auto-stash before pull $(Get-Date -Format s)" | Out-Null
  $stashed = $true
}

git fetch $Remote $Branch
git pull --ff-only $Remote $Branch

if ($stashed) {
  $entry = git stash list | Select-String "auto-stash before pull" | Select-Object -First 1
  if ($entry) {
    $name = ($entry.ToString()).Split(":")[0]
    git stash show -p $name > .git\auto-stash.diff
    git stash pop $name
  }
  Write-Host "差分は .git\auto-stash.diff を参照。必要な塊だけを add してください。"
}

git status

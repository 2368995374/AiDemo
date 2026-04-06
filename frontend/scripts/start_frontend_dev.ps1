Param(
  [switch]$InstallDeps = $false,
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "[Frontend] Working Dir: $PWD"

if ($InstallDeps) {
  Write-Host "[Frontend] Installing dependencies..."
  npm install
}

Write-Host "[Frontend] Starting Vite at http://127.0.0.1:$Port"
npm run dev -- --port $Port

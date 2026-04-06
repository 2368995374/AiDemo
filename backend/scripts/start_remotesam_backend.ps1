Param(
  [string]$Host = "0.0.0.0",
  [int]$Port = 8002,
  [string]$PythonExe = "D:/anacona/envs/remotesam_stable/python.exe",
  [switch]$DisableQwenLoad = $true
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path $PythonExe)) {
  throw "Python 不存在: $PythonExe"
}

if ($DisableQwenLoad) {
  # Avoid trying to load Qwen model in the RemoteSAM-only process.
  $env:MODEL_PATH = ""
}

Write-Host "[RemoteSAM] Using Python: $PythonExe"
Write-Host "[RemoteSAM] Working Dir: $PWD"
Write-Host "[RemoteSAM] Starting at http://$Host`:$Port"

& $PythonExe -m uvicorn app.main:app --host $Host --port $Port --reload

Param(
  [string]$Host = "0.0.0.0",
  [int]$Port = 8001,
  [string]$PythonExe = "D:/anacona/envs/zwyAi/python.exe"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path $PythonExe)) {
  throw "Python 不存在: $PythonExe"
}

Write-Host "[Qwen] Using Python: $PythonExe"
Write-Host "[Qwen] Working Dir: $PWD"
Write-Host "[Qwen] Starting at http://$Host`:$Port"

& $PythonExe -m uvicorn app.main:app --host $Host --port $Port --reload

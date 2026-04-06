Param(
  [switch]$InstallFrontendDeps = $false,
  [int]$QwenPort = 8001,
  [int]$RemoteSamPort = 8002,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$backendDir = (Join-Path $PSScriptRoot "..")
$workspaceDir = (Resolve-Path (Join-Path $backendDir "..")).Path
$frontendDir = Join-Path $workspaceDir "frontend"

$qwenScript = Join-Path $PSScriptRoot "start_qwen_backend.ps1"
$remotesamScript = Join-Path $PSScriptRoot "start_remotesam_backend.ps1"
$frontendScript = Join-Path $frontendDir "scripts/start_frontend_dev.ps1"

foreach ($path in @($qwenScript, $remotesamScript, $frontendScript)) {
  if (-not (Test-Path $path)) {
    throw "脚本不存在: $path"
  }
}

$shellCmd = "powershell.exe"

function Start-ServiceWindow {
  param(
    [string]$Title,
    [string]$ScriptPath,
    [string[]]$Args
  )

  $argList = @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $ScriptPath
  )
  if ($Args -and $Args.Count -gt 0) {
    $argList += $Args
  }

  Start-Process -FilePath $shellCmd -ArgumentList $argList -WindowStyle Normal | Out-Null
}

Write-Host "Starting Qwen backend window..."
Start-ServiceWindow -Title "Qwen Backend" -ScriptPath $qwenScript -Args @("-Port", "$QwenPort")

Start-Sleep -Milliseconds 500

Write-Host "Starting RemoteSAM backend window..."
Start-ServiceWindow -Title "RemoteSAM Backend" -ScriptPath $remotesamScript -Args @("-Port", "$RemoteSamPort")

Start-Sleep -Milliseconds 500

Write-Host "Starting Frontend window..."
$frontendArgs = @("-Port", "$FrontendPort")
if ($InstallFrontendDeps) {
  $frontendArgs = @("-InstallDeps", "-Port", "$FrontendPort")
}
Start-ServiceWindow -Title "Frontend Dev" -ScriptPath $frontendScript -Args $frontendArgs

Write-Host "Done. Three windows launched."
Write-Host "Qwen:      http://127.0.0.1:$QwenPort"
Write-Host "RemoteSAM: http://127.0.0.1:$RemoteSamPort"
Write-Host "Frontend:  http://127.0.0.1:$FrontendPort"

Param(
  [string]$Host = "0.0.0.0",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] 进入 backend 目录"
Set-Location $PSScriptRoot

Write-Host "[2/4] 激活本地环境（请按需修改）"
# 示例：conda activate RemoteSAM
# 如果你用 venv，可改成：. .\.venv\Scripts\Activate.ps1

Write-Host "[3/4] 安装后端基础依赖"
pip install -r requirements.txt

Write-Host "[4/4] 启动后端服务"
uvicorn app.main:app --host $Host --port $Port --reload

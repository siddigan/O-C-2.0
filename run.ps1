param(
    [string]$Host = '127.0.0.1',
    [int]$Port = 8000,
    [switch]$Reload
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PATH = "$root\.py312;$root\.py312\Scripts;$env:PATH"
$python = Join-Path $root '.py312\python.exe'

$reloadFlag = $Reload.IsPresent ? '--reload' : ''
& $python -m uvicorn app.main:app --host $Host --port $Port $reloadFlag

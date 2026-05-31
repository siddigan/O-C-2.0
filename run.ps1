param(
    [Alias('Host')]
    [string]$HostName = '127.0.0.1',
    [int]$Port = 8000,
    [switch]$Reload
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PATH = "$root\.py312;$root\.py312\Scripts;$env:PATH"
$python = Join-Path $root '.py312\python.exe'

$reloadFlag = if ($Reload.IsPresent) { '--reload' } else { '' }
& $python -m uvicorn app.main:app --host $HostName --port $Port $reloadFlag

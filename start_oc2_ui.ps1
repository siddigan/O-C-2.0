param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://${HostName}:${Port}/"
$healthUrl = "http://${HostName}:${Port}/health"
$out = Join-Path $root "logs\server.out.log"
$err = Join-Path $root "logs\server.err.log"

Add-Type -AssemblyName System.Windows.Forms

New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null

$isListening = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" -and $_.LocalAddress -in @($HostName, "0.0.0.0", "::") } |
    Select-Object -First 1

if (-not $isListening) {
    $argsList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "run.ps1"),
        "-Host", $HostName,
        "-Port", $Port
    )

    if ($Reload.IsPresent) {
        $argsList += "-Reload"
    }

    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $argsList `
        -WorkingDirectory $root `
        -RedirectStandardOutput $out `
        -RedirectStandardError $err `
        -WindowStyle Hidden | Out-Null
}

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Start-Process $url
} else {
    Start-Process (Join-Path $root "logs")
    [System.Windows.Forms.MessageBox]::Show(
        "OC2 server did not become ready on $healthUrl. Check logs\server.err.log.",
        "OC2 Launcher",
        "OK",
        "Warning"
    ) | Out-Null
}

$ErrorActionPreference = "Stop"
$apiKey = "sk-user--mjQjMNoOJqhR2atmLLmxW-P--x1R4XFZoIrj5qSobBfXALiwdBmA9m2h_YUlqlVXV_NnFXqPglYPVSXeej6QnymK7bnf9-lrZhMPD_CN6hZWHxyOQhXaErzp3cukP5bKgE"

# Kill any stale servers on our ports
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "3001|5173|3300" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Start Vite dev server
Write-Output "=== Starting Vite dev server on port 3001 ==="
$jb = Start-Job -ScriptBlock {
  param($d) Set-Location $d; npx vite dev --port 3001 --host 127.0.0.1 2>&1
} -ArgumentList "E:\New folder (2)\frontend-react"

# Wait for it to be ready
$maxWait = 30
$ready = $false
for ($i = 0; $i -lt $maxWait; $i++) {
  Start-Sleep -Seconds 1
  try {
    $r = Invoke-WebRequest -Uri http://127.0.0.1:3001/ -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch {}
}
if (-not $ready) { Write-Output "Server failed to start"; exit 1 }
Write-Output "Dev server ready on http://127.0.0.1:3001/"

# Run TestSprite tests
Write-Output "=== Running TestSprite tests ==="
$env:API_KEY = $apiKey
$output = & node "C:\Users\Rrs computers\AppData\Roaming\npm\node_modules\@testsprite\testsprite-mcp\dist\index.js" generateCodeAndExecute 2>&1
Write-Output $output

# Cleanup
Stop-Job $jb -ErrorAction SilentlyContinue
Remove-Job $jb -Force -ErrorAction SilentlyContinue

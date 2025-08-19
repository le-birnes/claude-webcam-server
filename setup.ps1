# Claude Webcam Server Installation Script
# This script sets up the auto-starting HTTPS webcam server for Claude

param(
    [string]$ClaudePath = "E:\Claude"
)

Write-Host "=== Claude Webcam Server Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "Node.js $nodeVersion found" -ForegroundColor Green
} catch {
    Write-Host "Node.js not found! Please install Node.js first." -ForegroundColor Red
    Write-Host "Download from: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# Set working directory
Set-Location $ClaudePath
Write-Host "Working directory: $ClaudePath" -ForegroundColor Gray

# Install required npm packages
Write-Host ""
Write-Host "Installing required npm packages..." -ForegroundColor Yellow
npm install express ws

# Check for SSL certificates
Write-Host ""
Write-Host "Checking SSL certificates..." -ForegroundColor Yellow
if (-not (Test-Path "server.key") -or -not (Test-Path "server.cert")) {
    Write-Host "SSL certificates not found. Generating self-signed certificates..." -ForegroundColor Yellow
    
    # Create OpenSSL config for certificate generation
    $opensslConfig = @"
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C=US
ST=State
L=City
O=Claude Webcam
OU=Development
CN=192.168.0.225
"@
    
    $opensslConfig | Out-File -FilePath "openssl.cnf" -Encoding ASCII
    
    # Generate certificates using OpenSSL
    & openssl req -new -x509 -days 365 -nodes -out server.cert -keyout server.key -config openssl.cnf
    
    if (Test-Path "server.cert" -and Test-Path "server.key") {
        Write-Host "SSL certificates generated successfully" -ForegroundColor Green
        Remove-Item "openssl.cnf" -ErrorAction SilentlyContinue
    } else {
        Write-Host "Failed to generate SSL certificates. Please install OpenSSL or create certificates manually." -ForegroundColor Red
    }
} else {
    Write-Host "SSL certificates found" -ForegroundColor Green
}

# Update or create claude_startup.ps1 if it doesn't have webcam server
Write-Host ""
Write-Host "Updating Claude startup script..." -ForegroundColor Yellow

$startupScriptPath = Join-Path $ClaudePath "claude_startup.ps1"
if (Test-Path $startupScriptPath) {
    $content = Get-Content $startupScriptPath -Raw
    if ($content -notmatch "webcam_server_https") {
        # Add webcam server startup before Claude launch
        $insertPoint = $content.IndexOf("# Start Claude in")
        if ($insertPoint -gt 0) {
            $before = $content.Substring(0, $insertPoint)
            $after = $content.Substring($insertPoint)
            $webcamStartup = @"
# Start HTTPS Webcam Server automatically
Write-Host "Starting HTTPS Webcam Server on port 8443..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "$ClaudePath\webcam_server_https.js" -WindowStyle Hidden
Write-Host "Webcam Server: https://192.168.0.225:8443/cam.html" -ForegroundColor Green

"@
            $newContent = $before + $webcamStartup + $after
            $newContent | Out-File -FilePath $startupScriptPath -Encoding UTF8
            Write-Host "Startup script updated" -ForegroundColor Green
        }
    } else {
        Write-Host "Webcam server already in startup script" -ForegroundColor Green
    }
}

# Create cam.html if it doesn't exist
if (-not (Test-Path "cam.html")) {
    Write-Host ""
    Write-Host "Creating cam.html..." -ForegroundColor Yellow
    # Copy from webcam_with_bridge.html or create new
    if (Test-Path "webcam_with_bridge.html") {
        Copy-Item "webcam_with_bridge.html" "cam.html"
        Write-Host "cam.html created" -ForegroundColor Green
    }
}

# Test the server
Write-Host ""
Write-Host "Starting test server..." -ForegroundColor Yellow
$testProcess = Start-Process -FilePath "node" -ArgumentList "webcam_server_https.js" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

if ($testProcess.HasExited) {
    Write-Host "Server test failed! Check webcam_server_https.js" -ForegroundColor Red
} else {
    Write-Host "Server test successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== Setup Complete ===" -ForegroundColor Green
    Write-Host "Webcam server will auto-start with Claude" -ForegroundColor Cyan
    Write-Host "Access from phone: https://192.168.0.225:8443/cam.html" -ForegroundColor Cyan
    Write-Host ""
    
    # Stop test server
    Stop-Process -Id $testProcess.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
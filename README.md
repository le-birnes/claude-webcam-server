# Claude Webcam Server

Auto-starting HTTPS webcam server for Claude that allows using your phone as a webcam.

## Features

- **Auto-starts with Claude** - No manual startup required
- **HTTPS secure connection** - Required for camera access
- **Simple URL access** - Just navigate to `/cam.html`
- **Phone-to-PC streaming** - Use your phone camera as PC webcam
- **Background operation** - Runs hidden, doesn't interfere with work

## Installation

### Prerequisites
- Node.js installed
- Claude CLI installed
- Windows PowerShell

### Quick Setup

1. Run the installation script:
```powershell
.\claude_webcam_setup.ps1
```

2. The script will:
   - Check Node.js installation
   - Install required npm packages (express, ws)
   - Generate SSL certificates if needed
   - Update Claude startup script
   - Create simplified cam.html access point
   - Test the server

### Manual Setup

1. Install dependencies:
```bash
npm install express ws
```

2. Generate SSL certificates:
```bash
openssl req -new -x509 -days 365 -nodes -out server.cert -keyout server.key
```

3. Add to `claude_startup.ps1`:
```powershell
# Start HTTPS Webcam Server automatically
Start-Process -FilePath "node" -ArgumentList "E:\Claude\webcam_server_https.js" -WindowStyle Hidden
```

## Usage

### From Phone
1. Connect to same WiFi as PC
2. Open browser and navigate to:
   ```
   https://192.168.0.225:8443/cam.html
   ```
3. Accept security certificate warning
4. Allow camera permissions
5. Click "Start Camera"

### Auto-start Camera
Add `?autostart=true` to URL:
```
https://192.168.0.225:8443/cam.html?autostart=true
```

### Server Management

Check if running:
```bash
tasklist | findstr node
```

Stop server (only when needed):
```bash
taskkill /IM node.exe /F
```

Restart server:
```bash
node E:\Claude\webcam_server_https.js
```

## Files

- `webcam_server_https.js` - Main HTTPS server
- `cam.html` - Simplified phone access page
- `claude_startup.ps1` - Auto-start script
- `server.cert` & `server.key` - SSL certificates
- `claude_webcam_setup.ps1` - Installation script

## Troubleshooting

### Connection Timeout
- Check Windows Firewall allows port 8443
- Verify phone is on same network
- Ensure server is running: `tasklist | findstr node`

### Certificate Warning
- This is normal for self-signed certificates
- Click "Advanced" → "Proceed to site"

### Camera Not Working
- Check browser camera permissions
- Try different browser (Chrome/Safari recommended)
- Ensure HTTPS (not HTTP) is used

## Security Notes

- Server uses self-signed SSL certificates
- Only accessible on local network
- No data leaves your network
- Camera stream is not recorded

## Integration with Claude

The webcam server is integrated into Claude's startup sequence. Every time Claude starts:
1. The HTTPS server launches automatically
2. Runs hidden in background
3. Available at `https://192.168.0.225:8443/cam.html`
4. Stays running until explicitly stopped

This ensures the webcam functionality is always available when using Claude.
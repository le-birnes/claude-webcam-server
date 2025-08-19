const https = require('https');
const fs = require('fs');
const path = require('path');
const express = require('express');
const WebSocket = require('ws');

const app = express();

// Serve static files
app.use(express.static(__dirname));

// Enable CORS for all routes
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    res.header('Access-Control-Allow-Credentials', 'true');
    
    if (req.method === 'OPTIONS') {
        res.sendStatus(200);
    } else {
        next();
    }
});

// Serve the HTML files
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'webcam_with_flip_control.html'));
});

app.get('/webcam_with_bridge.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'webcam_with_bridge.html'));
});

app.get('/webcam_with_flip_control.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'webcam_with_flip_control.html'));
});

app.get('/webcam_receiver.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'webcam_receiver.html'));
});

// SSL options for HTTPS
const serverOptions = {
    key: fs.readFileSync('server.key'),
    cert: fs.readFileSync('server.cert')
};

// Create HTTPS server
const server = https.createServer(serverOptions, app);

// Create WebSocket server for HTTPS
const wss = new WebSocket.Server({ 
    server,
    perMessageDeflate: false
});

let clients = new Set();

wss.on('connection', (ws) => {
    console.log('New WebSocket client connected (HTTPS)');
    clients.add(ws);
    
    ws.on('message', (message) => {
        // Broadcast to all other clients
        clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    });
    
    ws.on('close', () => {
        console.log('WebSocket client disconnected');
        clients.delete(ws);
    });
    
    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
        clients.delete(ws);
    });
});

const PORT = 8443;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`HTTPS Server running on https://192.168.0.225:${PORT}`);
    console.log(`WebSocket available on wss://192.168.0.225:${PORT}`);
    console.log('Access the camera at https://192.168.0.225:8443/webcam_with_bridge.html');
});
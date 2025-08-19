#!/usr/bin/env python3
"""
OBS Virtual Camera Bridge - Dynamic FPS Matching
Automatically matches phone camera's actual frame rate
"""

import asyncio
import websockets
import cv2
import numpy as np
import json
import base64
import sys
import os
import ssl
from PIL import Image
import io
import time
import threading
import queue
import statistics

try:
    import pyvirtualcam
except ImportError:
    print("Installing pyvirtualcam...")
    os.system("pip install pyvirtualcam")
    import pyvirtualcam

class OBSVirtualCameraBridge:
    def __init__(self, websocket_url="wss://192.168.0.225:8443/"):
        self.websocket_url = websocket_url
        self.virtual_cam = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = False
        self.last_frame = None
        self.frame_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_resolution = (1280, 720)  # Default resolution
        
        # Dynamic FPS detection
        self.detected_fps = 30.0
        self.frame_times = []
        self.fps_detection_samples = 30  # Sample last 30 frame intervals
        self.last_frame_time = time.time()
        
    async def connect_websocket(self):
        """Connect to WebSocket server and receive frames"""
        print(f"Connecting to WebSocket: {self.websocket_url}")
        
        try:
            # Create SSL context for self-signed certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(self.websocket_url, ssl=ssl_context) as websocket:
                print("[SUCCESS] Connected to WebSocket server")
                
                async for message in websocket:
                    if not self.running:
                        break
                        
                    try:
                        # Handle binary data (JPEG frames)
                        if isinstance(message, bytes):
                            self.process_frame(message)
                        else:
                            # Handle text messages
                            print(f"Received text message: {message}")
                            
                    except Exception as e:
                        print(f"Error processing frame: {e}")
                        continue
                        
        except websockets.exceptions.ConnectionClosed:
            print("[ERROR] WebSocket connection closed")
        except Exception as e:
            print(f"[ERROR] WebSocket error: {e}")
            
    def detect_fps(self):
        """Detect actual frame rate based on frame timing"""
        current_time = time.time()
        frame_interval = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        # Add to frame times list
        if frame_interval > 0.001:  # Ignore very small intervals
            self.frame_times.append(frame_interval)
            
            # Keep only recent samples
            if len(self.frame_times) > self.fps_detection_samples:
                self.frame_times.pop(0)
            
            # Calculate average FPS from recent samples
            if len(self.frame_times) >= 10:  # Need at least 10 samples
                avg_interval = statistics.mean(self.frame_times)
                new_fps = 1.0 / avg_interval
                
                # Only update if FPS changed significantly (>2 FPS difference)
                if abs(new_fps - self.detected_fps) > 2:
                    old_fps = self.detected_fps
                    self.detected_fps = round(new_fps, 1)
                    print(f"[FPS] Detected frame rate change: {old_fps} → {self.detected_fps} FPS")
                    return True
                    
        return False
            
    def process_frame(self, frame_data):
        """Process incoming frame data and detect resolution/FPS"""
        try:
            # Detect FPS from frame timing
            fps_changed = self.detect_fps()
            
            # Convert JPEG bytes to OpenCV image
            image = Image.open(io.BytesIO(frame_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Check if resolution changed
            new_resolution = (frame.shape[1], frame.shape[0])  # (width, height)
            resolution_changed = new_resolution != self.current_resolution
            
            if resolution_changed:
                print(f"[RESOLUTION] Changed from {self.current_resolution} to {new_resolution}")
                self.current_resolution = new_resolution
            
            # Add to frame queue (non-blocking)
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                # Remove old frame and add new one
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except queue.Empty:
                    pass
            
            # Update FPS counter
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 2.0:  # Report every 2 seconds
                input_fps = self.frame_count / 2.0
                self.frame_count = 0
                self.last_fps_time = current_time
                print(f"[VIDEO] Input: {input_fps:.1f} FPS, Detected: {self.detected_fps:.1f} FPS, Resolution: {new_resolution[0]}x{new_resolution[1]}, Queue: {self.frame_queue.qsize()}")
                
        except Exception as e:
            print(f"Error processing frame: {e}")
    
    def virtual_camera_thread(self):
        """Thread to handle virtual camera output"""
        print("[CAMERA] Starting OBS Virtual Camera...")
        
        try:
            # Start with default resolution
            width, height = self.current_resolution
            current_fps = self.detected_fps
            
            with pyvirtualcam.Camera(width=width, height=height, fps=int(current_fps), device='OBS Virtual Camera') as cam:
                print(f"[SUCCESS] OBS Virtual Camera started: {width}x{height} @ {int(current_fps)}fps")
                self.virtual_cam = cam
                
                # Create a default frame
                default_frame = np.zeros((height, width, 3), dtype=np.uint8)
                cv2.putText(default_frame, "Waiting for phone camera...", 
                           (width//2-200, height//2), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (255, 255, 255), 2)
                
                frame_time = 1.0 / current_fps
                last_time = time.time()
                output_fps_count = 0
                last_output_fps_time = time.time()
                
                while self.running:
                    try:
                        # Check if FPS changed significantly
                        if abs(self.detected_fps - current_fps) > 2:
                            print(f"[CAMERA] FPS changed from {current_fps} to {self.detected_fps}, adapting...")
                            current_fps = self.detected_fps
                            frame_time = 1.0 / current_fps
                        
                        # Get frame from queue or use last frame
                        frame = None
                        try:
                            frame = self.frame_queue.get_nowait()
                            self.last_frame = frame
                        except queue.Empty:
                            frame = self.last_frame if self.last_frame is not None else default_frame
                        
                        # Handle resolution changes
                        if frame is not None and frame.shape[:2] != (height, width):
                            # Resize frame to match camera (for now)
                            # TODO: Recreate camera with new resolution
                            frame = cv2.resize(frame, (width, height))
                        
                        # Convert BGR to RGB for pyvirtualcam
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Send to virtual camera
                        cam.send(frame_rgb)
                        
                        # Count output FPS
                        output_fps_count += 1
                        current_time = time.time()
                        if current_time - last_output_fps_time >= 2.0:  # Report every 2 seconds
                            actual_output_fps = output_fps_count / 2.0
                            print(f"[OUTPUT] Virtual Camera: {actual_output_fps:.1f} FPS (target: {current_fps:.1f})")
                            output_fps_count = 0
                            last_output_fps_time = current_time
                        
                        # Maintain frame rate based on detected FPS
                        elapsed = current_time - last_time
                        if elapsed < frame_time:
                            time.sleep(frame_time - elapsed)
                        last_time = time.time()
                        
                    except Exception as e:
                        print(f"Virtual camera error: {e}")
                        break
                        
        except Exception as e:
            print(f"[ERROR] Failed to start virtual camera: {e}")
            print("Make sure OBS Virtual Camera is installed and available")
            return False
            
        print("[CAMERA] Virtual camera stopped")
        return True
    
    async def start(self):
        """Start the bridge"""
        print("[START] Starting OBS Virtual Camera Bridge (Dynamic FPS)...")
        self.running = True
        
        # Start virtual camera in separate thread
        cam_thread = threading.Thread(target=self.virtual_camera_thread)
        cam_thread.daemon = True
        cam_thread.start()
        
        # Give camera thread time to start
        await asyncio.sleep(2)
        
        # Start WebSocket connection
        while self.running:
            try:
                await self.connect_websocket()
                if self.running:
                    print("[RETRY] Reconnecting in 3 seconds...")
                    await asyncio.sleep(3)
            except KeyboardInterrupt:
                print("\n[STOP] Stopping bridge...")
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                if self.running:
                    await asyncio.sleep(3)
    
    def stop(self):
        """Stop the bridge"""
        self.running = False

def main():
    """Main entry point"""
    print("=" * 65)
    print("OBS Virtual Camera Bridge - Dynamic FPS Matching")
    print("Automatically matches your phone camera's frame rate")
    print("=" * 65)
    
    bridge = OBSVirtualCameraBridge()
    
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        print("\n[STOP] Bridge stopped by user")
    except Exception as e:
        print(f"[ERROR] Bridge failed: {e}")
    finally:
        bridge.stop()

if __name__ == "__main__":
    main()
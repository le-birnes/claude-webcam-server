@echo off
title OBS Virtual Camera Bridge - Dynamic FPS
echo Starting OBS Virtual Camera Bridge (Dynamic FPS Matching)...
echo.
echo This bridge automatically matches your phone camera's frame rate
echo Make sure your phone is connected to: https://192.168.0.225:8443/cam.html
echo.
cd /d "E:\Claude"
py obs_bridge_dynamic_fps.py
pause
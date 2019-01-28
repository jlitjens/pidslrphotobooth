#!/bin/bash
echo "[LED] Setting inital PWM values via Pi-Blaster"
echo "17=0.05; 18=0.05; 22=0.05; 23=0.05" > /dev/pi-blaster
echo "[LED] Done"
echo "[PHOTOBOOTH] Starting Jimmy's photobooth"
sudo /usr/bin/python /home/pi/scripts/jlPhotobooth/jlphotobooth.py
echo "[SYSTEM] Ensure Pi-Blaster service is still running"
sudo systemctl restart pi-blaster
echo "[LED] Restting PWM values via Pi-Blaster"
echo "17=0.01; 18=0.05; 22=0.05; 23=0.05" > /dev/pi-blaster
echo "[LED] Done"
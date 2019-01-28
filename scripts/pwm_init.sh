#!/bin/bash
echo "[LED] Setting inital PWM values via Pi-Blaster"
echo "17=0.05; 18=0.05; 22=0.05; 23=0.05" > /dev/pi-blaster
echo "[LED] Done"
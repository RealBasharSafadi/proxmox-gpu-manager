#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash install.sh)"
    exit 1
fi

echo "Updating system and installing dependencies..."
apt update && apt install -y python3 python3-pip git python3-rich python3-proxmoxer

echo "Cloning the repository..."
if [ ! -d "/opt/proxmox-gpu-manager" ]; then
    git clone https://github.com/RealBasharSafadi/proxmox-gpu-manager.git /opt/proxmox-gpu-manager
fi

cd /opt/proxmox-gpu-manager

echo "Starting GPU Manager..."
sudo python3 gpu_manager.py

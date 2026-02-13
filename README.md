# Face-Locked Servo Control System

A distributed vision-control system that tracks face movement and controls a servo motor in real-time using MQTT communication and a web dashboard.

## 🎯 Overview

This system implements a complete distributed vision-control pipeline:

1. **PC Vision Node**: Detects faces using MediaPipe, determines movement state
2. **MQTT Communication**: Publishes movement commands to broker
3. **ESP-12E Controller**: Subscribes to commands and drives servo motor
4. **Backend Service**: Relays MQTT to WebSocket for real-time dashboard
5. **Web Dashboard**: Displays live movement status in browser

## 💻 Software Requirements

### PC (Vision Node)

- Python 3.8+
- OpenCV
- MediaPipe
- Paho-MQTT
- NumPy

### ESP-12E

- MicroPython firmware
- umqtt.simple library

### Backend Server

- Node.js 18+
- Mosquitto MQTT broker
- npm packages: mqtt, ws, express

---

## 📦 Installation Guide

### 1. Clone Repository

```bash
git clone https://github.com/Aimable01/face-locked-servo.git
cd face-locked-servo
```

### 2. PC Setup (Vision Node)

```bash
cd pc
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Backend Setup

```bash
cd backend
npm install
```

### 4. ESP-12E Setup

```bash
# Install esptool
pip install esptool adafruit-ampy

# Download MicroPython firmware
# From: https://micropython.org/download/esp8266/

# Flash firmware (replace COM3 with your port)
esptool.py --port COM3 erase_flash
esptool.py --port COM3 --baud 460800 write_flash --flash_size=detect 0 esp8266-20230426-v1.20.0.bin
```

---

## 🧪 Local Testing

### Step 1: Start MQTT Broker

```bash
# Windows (as Administrator)
net start mosquitto
# or
mosquitto -v

# macOS
brew services start mosquitto

# Linux
sudo systemctl start mosquitto
```

### Step 2: Start Backend Service

```bash
cd backend
npm start
# WebSocket on port 9002, Dashboard on http://localhost:3000
```

### Step 3: Monitor ESP Logs

```bash
# Find your COM port
# Windows: COM3, Mac: /dev/cu.usbserial-*, Linux: /dev/ttyUSB0

python test/serial_monitor.py
# or
screen /dev/ttyUSB0 115200
```

### Step 4: Run Vision Node

```bash
cd pc
python vision_node.py
# Press 'q' to quit
```

### Step 5: Open Dashboard

- Browser: http://localhost:3000
- Real-time updates should appear

---

## ☁️ Deployment to VPS

### 1. Connect to VPS

```bash
ssh user351@157.173.101.159
# Password: r9@M!6Q2 (change on first login)
```

### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Mosquitto
sudo apt install -y mosquitto mosquitto-clients

# Configure Mosquitto for external access
sudo nano /etc/mosquitto/mosquitto.conf
# Add:
# listener 1883 0.0.0.0
# allow_anonymous true

sudo systemctl restart mosquitto

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2
sudo npm install -g pm2
```

### 3. Deploy Backend

```bash
# Create project directory
mkdir -p ~/face-locked-servo/backend
cd ~/face-locked-servo/backend

# Copy your files (using SCP or nano)
# ... upload backend files ...

# Install dependencies
npm install

# Start with PM2
pm2 start mqtt_websocket_bridge.js --name face-locked-servo
pm2 save
pm2 startup

# Configure firewall
sudo ufw allow 1883/tcp
sudo ufw allow 9002/tcp
sudo ufw allow 3000/tcp
sudo ufw enable
```

### 4. Update ESP-12E Code

```python
# In esp8266/main.py, update:
MQTT_BROKER = "157.173.101.159"  # VPS IP
```

---

## 🎮 Usage Instructions

### Starting the System

1. **Power ESP-12E** (connect USB)
2. **Start Mosquitto** on VPS or local PC
3. **Start Backend** (`npm start`)
4. **Run Vision Node** (`python pc/vision_node.py`)
5. **Open Dashboard** (http://localhost:3000 or http://157.173.101.159:3000)

### Controls

| Key     | Function                    |
| ------- | --------------------------- |
| `q`     | Quit vision node            |
| `+`/`=` | Increase distance threshold |
| `-`     | Decrease distance threshold |
| `d`     | Toggle debug overlay        |

### Movement States

| State        | Description          | Servo Position     |
| ------------ | -------------------- | ------------------ |
| `MOVE_LEFT`  | Face left of center  | 45°                |
| `MOVE_RIGHT` | Face right of center | 135°               |
| `CENTERED`   | Face centered        | 90°                |
| `NO_FACE`    | No face detected     | Hold last position |

---

## 🔍 Troubleshooting

### ESP-12E Not Connecting

| Symptom          | Check                                          |
| ---------------- | ---------------------------------------------- |
| No serial output | USB connection, correct COM port, 115200 baud  |
| WiFi fails       | SSID/password, signal strength, 2.4GHz network |
| MQTT fails       | Broker IP, firewall, Mosquitto running         |

### Servo Not Moving

| Symptom         | Check                                |
| --------------- | ------------------------------------ |
| No movement     | Power (5V), signal wire (D5), ground |
| Jittery         | Add capacitor, external power        |
| Wrong direction | Swap left/right angles in code       |

### MQTT Issues

```bash
# Test MQTT from PC
mosquitto_sub -h 157.173.101.159 -t "vision/team351/#" -v

# Test from ESP
# In serial monitor, you should see "✅ Subscribed"
```

### Common Fixes

```bash
# Restart Mosquitto
sudo systemctl restart mosquitto

# Check Mosquitto status
sudo systemctl status mosquitto

# View Mosquitto logs
sudo journalctl -u mosquitto -f

# Check if port is listening
sudo netstat -tlnp | grep 1883
```

---

### MQTT Topics

| Topic                       | Purpose                | Published By |
| --------------------------- | ---------------------- | ------------ |
| `vision/teamWIGO/movement`  | Face movement commands | PC Node      |
| `vision/teamWIGO/heartbeat` | System status          | PC + ESP     |

### Payload Format

```json
{
  "status": "MOVE_LEFT",
  "confidence": 0.95,
  "timestamp": 1730000000
}
```

---

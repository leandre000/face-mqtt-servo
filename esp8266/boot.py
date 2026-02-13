# boot.py - Run on ESP8266 startup
import network
import time
import machine

def connect_wifi():
    ssid = "YOUR_WIFI_SSID"
    password = "YOUR_WIFI_PASSWORD"
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("[WiFi] Connecting to", ssid)
        wlan.connect(ssid, password)
        
        max_wait = 30
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            time.sleep(1)
            print("[WiFi] Waiting...")
    
    if wlan.isconnected():
        print("[WiFi] Connected!", wlan.ifconfig())
        return True
    else:
        print("[WiFi] Connection failed!")
        return False

connect_wifi()
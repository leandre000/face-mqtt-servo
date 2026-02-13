"""
ESP8266 Edge Controller
- Subscribes to MQTT movement messages
- Interprets movement instructions
- Drives servo motor

Must NOT:
- Use HTTP
- Use WebSocket
- Connect directly to browser
"""

import json
import time
from machine import Pin, PWM
from umqtt.simple import MQTTClient
import network

# Configuration
TEAM_ID = "teamWIGO"  #
MQTT_BROKER = "157.173.101.159"  # VPS IP
MQTT_PORT = 1883
CLIENT_ID = f"esp8266_{TEAM_ID}"

# Servo configuration
SERVO_PIN = 15  # GPIO15 (D8 on many boards)
servo = None

# Movement state mapping
ANGLE_CENTER = 90
ANGLE_LEFT = 45
ANGLE_RIGHT = 135

# Deadzone for no movement
DEADZONE = 0.05  # 5% tolerance

def setup_servo():
    """Initialize servo on specified pin"""
    global servo
    pwm = PWM(Pin(SERVO_PIN))
    pwm.freq(50)  # Standard 50Hz servo frequency
    servo = pwm
    set_angle(ANGLE_CENTER)
    time.sleep(1)
    print("[Servo] Initialized at center position")

def set_angle(angle):
    """
    Set servo angle (0-180 degrees)
    Pulse width: 0.5ms (0°) to 2.5ms (180°) @ 50Hz (20ms period)
    """
    if servo is None:
        return
    
    # Clamp angle
    angle = max(0, min(180, angle))
    
    # Convert angle to duty cycle
    # 0° = 0.5ms = 2.5% duty = 25 (for 0-1023 range)
    # 180° = 2.5ms = 12.5% duty = 128 (for 0-1023 range)
    duty = int(25 + (angle / 180) * 103)
    servo.duty(duty)
    print(f"[Servo] Angle set to {angle}°")

def map_state_to_angle(state):
    """Convert movement state to servo angle"""
    if state == "MOVE_LEFT":
        return ANGLE_LEFT
    elif state == "MOVE_RIGHT":
        return ANGLE_RIGHT
    elif state == "CENTERED":
        return ANGLE_CENTER
    else:  # NO_FACE - stay at current position
        return None

def mqtt_callback(topic, msg):
    """Handle incoming MQTT messages"""
    try:
        topic_str = topic.decode()
        payload = json.loads(msg.decode())
        
        print(f"[MQTT] Received on {topic_str}")
        print(f"[MQTT] Payload: {payload}")
        
        # Only process our movement topic
        expected_topic = f"vision/{TEAM_ID}/movement"
        
        if topic_str == expected_topic:
            status = payload.get("status")
            timestamp = payload.get("timestamp")
            
            angle = map_state_to_angle(status)
            if angle is not None:
                set_angle(angle)
                
    except Exception as e:
        print(f"[Error] MQTT callback: {e}")

def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
        client.set_callback(mqtt_callback)
        client.connect()
        
        # Subscribe to movement topic
        topic = f"vision/{TEAM_ID}/movement"
        client.subscribe(topic)
        print(f"[MQTT] Subscribed to {topic}")
        
        return client
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")
        return None

def main():
    print("\n=== ESP8266 Face-Locked Servo Controller ===")
    print(f"Team ID: {TEAM_ID}")
    print(f"MQTT Broker: {MQTT_BROKER}")
    
    # Initialize servo
    setup_servo()
    
    # Connect to MQTT
    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        print("[Error] Could not connect to MQTT. Rebooting...")
        time.sleep(2)
        machine.reset()
    
    print("[System] Ready. Waiting for movement commands...")
    
    # Keep-alive counter
    last_heartbeat = time.time()
    
    try:
        while True:
            # Check for MQTT messages
            mqtt_client.check_msg()
            
            # Send heartbeat every 30 seconds
            if time.time() - last_heartbeat > 30:
                heartbeat = {
                    "node": "esp8266",
                    "status": "ONLINE",
                    "timestamp": int(time.time())
                }
                mqtt_client.publish(f"vision/{TEAM_ID}/heartbeat", 
                                   json.dumps(heartbeat))
                last_heartbeat = time.time()
            
            time.sleep(0.05)  # 20Hz control loop
            
    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
        # Return servo to center on exit
        set_angle(ANGLE_CENTER)
        time.sleep(0.5)
        mqtt_client.disconnect()
        
if __name__ == "__main__":
    main()
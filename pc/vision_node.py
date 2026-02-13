"""
PC Vision Node
- Captures camera frames
- Detects and tracks faces
- Determines movement state
- Publishes MQTT messages to VPS broker

Must NOT:
- Communicate directly with ESP8266
- Communicate directly with browser
- Use HTTP/WebSocket for device communication
"""

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import json
import time
from pathlib import Path
from typing import Optional, Tuple
import sys
from dataclasses import asdict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pc.config import MQTTConfig, MovementState

try:
    import mediapipe as mp
except ImportError:
    mp = None
    print("MediaPipe not installed. Please install: pip install mediapipe")

class FaceTracker:
    def __init__(self):
        # MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range (2m), 1 for long-range (5m)
            min_detection_confidence=0.5
        )
        
        # Smoothing
        self.prev_face_center: Optional[float] = None
        self.smooth_factor = 0.6
        self.frame_width = 640
        self.frame_height = 480
        
    def get_face_center(self, frame: np.ndarray) -> Tuple[Optional[float], Optional[np.ndarray]]:
        """Returns (x_center_normalized, face_bbox)"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb)
        
        if not results.detections:
            self.prev_face_center = None
            return None, None
            
        # Get first face
        detection = results.detections[0]
        bbox = detection.location_data.relative_bounding_box
        
        # Calculate face center (normalized 0-1)
        x_center = bbox.xmin + bbox.width / 2
        
        # Smoothing
        if self.prev_face_center is None:
            self.prev_face_center = x_center
        else:
            self.prev_face_center = (
                self.smooth_factor * self.prev_face_center + 
                (1 - self.smooth_factor) * x_center
            )
            
        # Convert to pixel coordinates for visualization
        h, w = frame.shape[:2]
        bbox_pixels = (
            int(bbox.xmin * w),
            int(bbox.ymin * h),
            int(bbox.width * w),
            int(bbox.height * h)
        )
        
        return self.prev_face_center, bbox_pixels
    
    def determine_state(self, face_center: Optional[float]) -> str:
        """Determine movement state based on face position"""
        if face_center is None:
            return MovementState.NO_FACE
            
        # Face center is normalized 0-1, convert to -1 to 1 range
        # 0 = left edge, 0.5 = center, 1 = right edge
        deviation = face_center - 0.5
        
        if abs(deviation) < (MovementState.DEADZONE / self.frame_width):
            return MovementState.CENTERED
        elif deviation < 0:
            return MovementState.MOVE_LEFT
        else:
            return MovementState.MOVE_RIGHT

class MQTTPublisher:
    def __init__(self, config: MQTTConfig):
        self.config = config
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Connected to broker at {self.config.broker_host}")
        else:
            print(f"[MQTT] Connection failed with code {rc}")
            
    def on_publish(self, client, userdata, mid):
        print(f"[MQTT] Message published (mid: {mid})")
        
    def connect(self):
        try:
            self.client.connect(self.config.broker_host, self.config.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False
            
    def publish_movement(self, status: str, confidence: float = 1.0):
        payload = {
            "status": status,
            "confidence": confidence,
            "timestamp": int(time.time())
        }
        
        topic = self.config.movement_topic
        self.client.publish(topic, json.dumps(payload), qos=1)
        print(f"[MQTT] Published {status} to {topic}")
        
    def publish_heartbeat(self, status: str = "ONLINE"):
        payload = {
            "node": "pc",
            "status": status,
            "timestamp": int(time.time())
        }
        
        topic = self.config.heartbeat_topic
        self.client.publish(topic, json.dumps(payload), qos=1)
        
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

def main():
    # Configuration
    config = MQTTConfig(team_id="team351")  # Use your username
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Initialize components
    tracker = FaceTracker()
    mqtt_client = MQTTPublisher(config)
    
    if not mqtt_client.connect():
        print("[ERROR] Failed to connect to MQTT broker")
        return
        
    # Send initial heartbeat
    mqtt_client.publish_heartbeat()
    
    print("\n=== Face-Locked Servo Control - Phase 1 ===")
    print(f"Team ID: {config.team_id}")
    print(f"MQTT Topic: {config.movement_topic}")
    print("Press 'q' to quit\n")
    
    # FPS calculation
    fps = 0
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Mirror frame for intuitive control
            frame = cv2.flip(frame, 1)
            
            # Detect face and determine state
            face_center, bbox = tracker.get_face_center(frame)
            state = tracker.determine_state(face_center)
            
            # Publish movement state
            if state != MovementState.NO_FACE:
                mqtt_client.publish_movement(state, confidence=0.95)
            else:
                mqtt_client.publish_movement(MovementState.NO_FACE, confidence=0.0)
            
            # Visualize
            vis = frame.copy()
            
            # Draw vertical center line
            h, w = vis.shape[:2]
            cv2.line(vis, (w//2, 0), (w//2, h), (255, 255, 255), 1)
            
            # Draw deadzone boundaries
            deadzone_pixels = MovementState.DEADZONE
            cv2.line(vis, (w//2 - deadzone_pixels, 0), 
                    (w//2 - deadzone_pixels, h), (200, 200, 200), 1)
            cv2.line(vis, (w//2 + deadzone_pixels, 0), 
                    (w//2 + deadzone_pixels, h), (200, 200, 200), 1)
            
            # Draw face detection
            if bbox is not None:
                x, y, w_box, h_box = bbox
                # Color coding based on state
                if state == MovementState.CENTERED:
                    color = (0, 255, 0)  # Green
                elif state == MovementState.MOVE_LEFT:
                    color = (255, 0, 0)  # Blue
                elif state == MovementState.MOVE_RIGHT:
                    color = (0, 0, 255)  # Red
                else:
                    color = (128, 128, 128)  # Gray
                    
                cv2.rectangle(vis, (x, y), (x + w_box, y + h_box), color, 2)
                
                # Draw face center
                center_x = int(face_center * w) if face_center else x + w_box//2
                cv2.circle(vis, (center_x, y + h_box//2), 5, color, -1)
            
            # FPS calculation
            frame_count += 1
            if frame_count >= 30:
                fps = frame_count / (time.time() - start_time)
                frame_count = 0
                start_time = time.time()
            
            # Overlay status
            cv2.putText(vis, f"Team: {config.team_id}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(vis, f"State: {state}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f"FPS: {fps:.1f}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(vis, "Press 'q' to quit", (10, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.imshow("Vision Node - Face Tracking", vis)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        mqtt_client.disconnect()
        print("\n[System] Shutdown complete")

if __name__ == "__main__":
    main()
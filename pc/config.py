import json
from dataclasses import dataclass
from typing import Tuple

@dataclass
class MQTTConfig:
    broker_host: str = "157.173.101.159"  # VPS IP
    broker_port: int = 1883
    team_id: str = "teamWIGO"  # Use your username as team_id
    base_topic: str = "vision"
    
    @property
    def movement_topic(self) -> str:
        return f"{self.base_topic}/{self.team_id}/movement"
    
    @property
    def heartbeat_topic(self) -> str:
        return f"{self.base_topic}/{self.team_id}/heartbeat"

@dataclass
class MovementState:
    NO_FACE = "NO_FACE"
    CENTERED = "CENTERED"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    
    # Deadzone thresholds (pixels from center)
    DEADZONE = 30
    # Servo angle mapping
    ANGLE_CENTER = 90
    ANGLE_LEFT = 45
    ANGLE_RIGHT = 135
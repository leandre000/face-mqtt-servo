/**
 * Backend API Service (VPS)
 * - Hosts MQTT broker (Port 1883) - requires Mosquitto
 * - Hosts WebSocket API service (Port 9002)
 * - Subscribes to MQTT movement messages
 * - Pushes real-time updates to browsers via WebSocket
 *
 * The backend relays real-time events.
 */

const express = require("express");
const WebSocket = require("ws");
const mqtt = require("mqtt");
const path = require("path");

// Configuration
const CONFIG = {
  // MQTT (broker should be running separately on port 1883)
  mqttBroker: "mqtt://localhost:1883",

  // WebSocket server port
  wsPort: 9002,

  // HTTP server port for serving dashboard
  httpPort: 3000,

  // Teams to monitor (add your team_id)
  teams: ["teamWIGO"],
};

// Store latest movement states per team
const movementStates = new Map();

// Initialize MQTT client
console.log(`[Backend] Connecting to MQTT broker at ${CONFIG.mqttBroker}`);
const mqttClient = mqtt.connect(CONFIG.mqttBroker);

mqttClient.on("connect", () => {
  console.log("[MQTT] Connected to broker");

  // Subscribe to all team movement topics
  CONFIG.teams.forEach((team) => {
    const topic = `vision/${team}/movement`;
    mqttClient.subscribe(topic, (err) => {
      if (!err) {
        console.log(`[MQTT] Subscribed to ${topic}`);
      }
    });

    // Also subscribe to heartbeats
    const heartbeatTopic = `vision/${team}/heartbeat`;
    mqttClient.subscribe(heartbeatTopic, (err) => {
      if (!err) {
        console.log(`[MQTT] Subscribed to ${heartbeatTopic}`);
      }
    });
  });
});

mqttClient.on("message", (topic, message) => {
  try {
    const payload = JSON.parse(message.toString());
    console.log(`[MQTT] Received on ${topic}:`, payload);

    // Extract team_id from topic
    const topicParts = topic.split("/");
    if (topicParts.length >= 2) {
      const teamId = topicParts[1];

      // Store the latest state
      movementStates.set(teamId, {
        ...payload,
        topic,
        receivedAt: Date.now(),
      });

      // Broadcast to all connected WebSocket clients
      broadcastToWebSockets({
        type: "movement_update",
        team: teamId,
        data: payload,
        timestamp: Date.now(),
      });
    }
  } catch (error) {
    console.error("[MQTT] Error processing message:", error);
  }
});

// WebSocket server
const wss = new WebSocket.Server({ port: CONFIG.wsPort });

wss.on("listening", () => {
  console.log(`[WebSocket] Server running on port ${CONFIG.wsPort}`);
});

wss.on("connection", (ws) => {
  console.log("[WebSocket] Client connected");

  // Send current states to newly connected client
  const currentStates = {};
  movementStates.forEach((state, teamId) => {
    currentStates[teamId] = state;
  });

  ws.send(
    JSON.stringify({
      type: "initial_state",
      data: currentStates,
      timestamp: Date.now(),
    }),
  );

  ws.on("close", () => {
    console.log("[WebSocket] Client disconnected");
  });
});

// Broadcast to all WebSocket clients
function broadcastToWebSockets(message) {
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

// Express server for serving dashboard
const app = express();
app.use(express.static(path.join(__dirname, "public")));

app.get("/api/status", (req, res) => {
  const states = {};
  movementStates.forEach((state, teamId) => {
    states[teamId] = state;
  });

  res.json({
    teams: CONFIG.teams,
    movementStates: states,
    wsPort: CONFIG.wsPort,
    timestamp: Date.now(),
  });
});

app.listen(CONFIG.httpPort, () => {
  console.log(`[HTTP] Dashboard server running on port ${CONFIG.httpPort}`);
  console.log(
    `[HTTP] Open http://localhost:${CONFIG.httpPort} to view dashboard`,
  );
});

// Handle shutdown
process.on("SIGINT", () => {
  console.log("\n[Backend] Shutting down...");
  mqttClient.end();
  wss.close();
  process.exit();
});

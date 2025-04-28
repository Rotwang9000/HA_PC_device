#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ESP_Knob.h>
#include <ArduinoJson.h>

// OLED settings
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_I2C_ADDRESS 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Wi-Fi and MQTT settings
const char* ssid = "GeeGee";
const char* password = "LilyLola";
const char* mqtt_server = "192.168.1.15";
const char* mqtt_user = "devices";
const char* mqtt_pass = "LilyLola";

// Entity definitions
struct Entity {
  const char* entityId;
  const char* friendlyName;
  const char* domain; // "light", "media_player", or "computer"
};

const Entity entities[] = {
  {"light.gold_light", "Gold Light", "light"},
  {"light.led_flood_light", "Living Room Flood", "light"},
  {"media_player.lgnano_55", "LG Nano 55", "media_player"},
  {"computer.FelixLaptop", "Felix Laptop", "computer"}
};
const int numEntities = sizeof(entities) / sizeof(entities[0]);
int currentEntityIndex = 0;

// MQTT topics
struct MqttTopics {
  String command;
  String requestState;
  String brightness;
  String hs;
  String volume;
  String source;
  String update;
  String mute;      // For computer
  String lock;      // For computer
  String enforceLock; // For computer enforce lock toggle
};

MqttTopics topics;

void updateTopics() {
  const Entity& entity = entities[currentEntityIndex];
  String baseTopic = String("homeassistant/") + entity.domain + "/" + entity.entityId + "/";
  topics.command = baseTopic + "set";
  topics.requestState = baseTopic + "request_state";
  topics.update = baseTopic + "update";

  // Domain-specific topics
  if (strcmp(entity.domain, "light") == 0) {
    topics.brightness = baseTopic + "brightness";
    topics.hs = baseTopic + "hs";
    topics.volume = "";
    topics.source = "";
    topics.mute = "";
    topics.lock = "";
  } else if (strcmp(entity.domain, "media_player") == 0) {
    topics.volume = baseTopic + "volume";
    topics.source = baseTopic + "source";
    topics.brightness = "";
    topics.hs = "";
    topics.mute = "";
    topics.lock = "";
  } else if (strcmp(entity.domain, "computer") == 0) {
    // Use the correct MQTT topic for computer integration
    String computerName = String(entity.entityId).substring(String(entity.entityId).indexOf(".") + 1).toLowerCase();
    String computerBase = "homeassistant/Computer/Computer." + computerName;
    
    // Main entity topics
    topics.command = computerBase + "/set";
    topics.requestState = computerBase + "/request_state";
    topics.update = computerBase + "/update";
    
    // Helper entity topics - use proper entity ID format with dots
    topics.volume = "homeassistant/number/computer." + computerName + ".volume/set";
    topics.mute = "homeassistant/switch/computer." + computerName + ".mute/toggle";
    topics.lock = "homeassistant/button/computer." + computerName + ".lock/press";
    topics.enforceLock = "homeassistant/switch/computer." + computerName + ".enforce_lock/set";
    
    topics.brightness = "";
    topics.hs = "";
    topics.source = "";
  }
  Serial.print("Updated topics for entity: ");
  Serial.print(entity.entityId);
  Serial.print(", domain: ");
  Serial.println(entity.domain);
  Serial.print("Command topic: ");
  Serial.println(topics.command);
  Serial.print("Volume topic: ");
  Serial.println(topics.volume);
  Serial.print("Update topic: ");
  Serial.println(topics.update);
}

// Pin definitions
const int onboardLedPin = 2;
const int buttonPin = 4;
const int buttonLedPin = 5;
const int encoderTRA = 25;
const int encoderTRB = 26;
const int encoderPUSH = 27;
const int backButton = 14;
const int leftButton = 12;

// MQTT client
WiFiClient espClient;
PubSubClient client(espClient);

// Encoder
ESP_Knob *knob;

// Light colors
const float colors[][2] = {
  {0, 100}, {120, 100}, {240, 100}, {60, 100}, {300, 100}, {180, 100}, {0, 0}, {36, 100}
};
const char* colorNames[] = {
  "Red", "Green", "Blue", "Yellow", "Magenta", "Cyan", "White", "WarmWhite"
};
const int numColors = sizeof(colors) / sizeof(colors[0]);

// TV sources
const char* tvSources[] = {
  "Disney+", "Jellyfin", "Max", "Netflix", "Prime Video", "Roku",
  "SVT Play", "TV4 Play", "Telia Play", "YouTube", "HDMI 3"
};
const int numTvSources = sizeof(tvSources) / sizeof(tvSources[0]);
int currentTvSourceIndex = 0;
int currentTvTargetSourceIndex = -1;

// Entity states
bool entityStates[numEntities] = {false};
int displayBrightness[numEntities] = {128}; // For lights
int targetBrightness[numEntities] = {128};  // For lights
int colorIndices[numEntities] = {0};        // For lights
int volumeLevels[numEntities] = {13};       // For TV and computer (0-100)
int targetVolumeLevels[numEntities] = {13}; // For TV and computer
bool stateReceived[numEntities] = {false};
String pcActiveWindow = "";                 // For computer active window
String pcSessionState = "unknown";          // For computer lock state (locked/unlocked)

// Variables
bool connected = false;
unsigned long lastRequestTime = 0;
const unsigned long requestInterval = 5000;
unsigned long lastKnobActivity = 0;
const unsigned long knobIdleTimeout = 100;
bool lastButtonState = LOW;
bool lastPushButtonState = HIGH;
bool lastBackButtonState = HIGH;
bool lastLeftButtonState = HIGH;
bool oledAttached = false;
unsigned long lastOledCheck = 0;
const unsigned long oledCheckInterval = 1000;

// Debouncing for rotary encoder
int lastCount = 0;
int directionCounter = 0;
const int directionThreshold = 2;
bool lastDirection = true;

// Check if OLED is attached
bool checkOledAttached() {
  Wire.beginTransmission(OLED_I2C_ADDRESS);
  bool attached = Wire.endTransmission() == 0;
  if(!attached){
    Serial.print("Checking OLED attachment: ");
    Serial.println(attached ? "Attached" : "Not attached");
  }
  return attached;
}

// Encoder callbacks
void onKnobLeftEventCallback(int count, void *usr_data) {
  if (!oledAttached) {
    Serial.println("Knob left event ignored: OLED not attached");
    return;
  }

  const Entity& entity = entities[currentEntityIndex];
  // For computer, allow volume adjustment if unlocked, regardless of entityStates
  bool canAdjust = (strcmp(entity.domain, "computer") == 0 && pcSessionState == "unlocked") || 
                   (strcmp(entity.domain, "computer") != 0 && entityStates[currentEntityIndex]);
  if (!canAdjust) {
    Serial.print("Knob left event ignored for ");
    Serial.print(entity.entityId);
    Serial.print(": computer locked or entity state is off (");
    Serial.print(entityStates[currentEntityIndex] ? "on" : "off");
    Serial.println(")");
    return;
  }

  if (lastDirection && count < lastCount) {
    directionCounter = 0;
    lastDirection = false;
    Serial.println("Knob direction changed to left");
  }

  directionCounter--;
  lastCount = count;

  if (directionCounter <= -directionThreshold) {
    if (strcmp(entity.domain, "light") == 0) {
      targetBrightness[currentEntityIndex] = max(0, targetBrightness[currentEntityIndex] - 5);
      Serial.printf("Knob left, brightness for %s: %d\n", entity.entityId, targetBrightness[currentEntityIndex]);
    } else {
      targetVolumeLevels[currentEntityIndex] = max(0, targetVolumeLevels[currentEntityIndex] - 2);
      Serial.printf("Knob left, volume for %s: %d\n", entity.entityId, targetVolumeLevels[currentEntityIndex]);
    }
    lastKnobActivity = millis();
    updateDisplay();
    directionCounter = 0;
  }
}

void onKnobRightEventCallback(int count, void *usr_data) {
  if (!oledAttached) {
    Serial.println("Knob right event ignored: OLED not attached");
    return;
  }

  const Entity& entity = entities[currentEntityIndex];
  // For computer, allow volume adjustment if unlocked, regardless of entityStates
  bool canAdjust = (strcmp(entity.domain, "computer") == 0 && pcSessionState == "unlocked") || 
                   (strcmp(entity.domain, "computer") != 0 && entityStates[currentEntityIndex]);
  if (!canAdjust) {
    Serial.print("Knob right event ignored for ");
    Serial.print(entity.entityId);
    Serial.print(": computer locked or entity state is off (");
    Serial.print(entityStates[currentEntityIndex] ? "on" : "off");
    Serial.println(")");
    return;
  }

  if (!lastDirection && count > lastCount) {
    directionCounter = 0;
    lastDirection = true;
    Serial.println("Knob direction changed to right");
  }

  directionCounter++;
  lastCount = count;

  if (directionCounter >= directionThreshold) {
    if (strcmp(entity.domain, "light") == 0) {
      targetBrightness[currentEntityIndex] = min(255, targetBrightness[currentEntityIndex] + 5);
      Serial.printf("Knob right, brightness for %s: %d\n", entity.entityId, targetBrightness[currentEntityIndex]);
    } else {
      targetVolumeLevels[currentEntityIndex] = min(100, targetVolumeLevels[currentEntityIndex] + 2);
      Serial.printf("Knob right, volume for %s: %d\n", entity.entityId, targetVolumeLevels[currentEntityIndex]);
    }
    lastKnobActivity = millis();
    updateDisplay();
    directionCounter = 0;
  }
}

void onKnobZeroEventCallback(int count, void *usr_data) {
  if (!oledAttached) {
    Serial.println("Knob zero event ignored: OLED not attached");
    return;
  }
  directionCounter = 0;
  lastCount = 0;
  lastDirection = true;
  Serial.println("Knob zero event, resetting direction");
}

void setup() {
  pinMode(onboardLedPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLDOWN);
  pinMode(buttonLedPin, OUTPUT);
  pinMode(backButton, INPUT_PULLUP);
  pinMode(leftButton, INPUT_PULLUP);
  pinMode(encoderPUSH, INPUT_PULLUP);

  digitalWrite(onboardLedPin, HIGH);
  digitalWrite(buttonLedPin, entityStates[currentEntityIndex]);

  Serial.begin(115200);
  Serial.println("Starting setup...");
  delay(1000);

  Wire.begin();
  Serial.println("I2C bus initialized");

  oledAttached = checkOledAttached();
  if (oledAttached && !display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS)) {
    Serial.println("OLED detected but failed to initialize!");
    oledAttached = false;
  } else if (oledAttached) {
    Serial.println("OLED successfully initialized");
  }

  if (oledAttached) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(F("Connecting..."));
    display.display();
    Serial.println("OLED display set to 'Connecting...'");
  }

  knob = new ESP_Knob(encoderTRA, encoderTRB);
  knob->begin();
  knob->attachLeftEventCallback(onKnobLeftEventCallback);
  knob->attachRightEventCallback(onKnobRightEventCallback);
  knob->attachZeroEventCallback(onKnobZeroEventCallback);
  Serial.println("Rotary encoder initialized and callbacks attached");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print("WiFi attempt ");
    Serial.print(attempts + 1);
    Serial.print(": Status = ");
    Serial.println(WiFi.status());
    attempts++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Failed to connect to Wi-Fi");
    if (oledAttached) {
      display.clearDisplay();
      display.setCursor(0, 0);
      display.println(F("Wi-Fi Failed"));
      display.display();
      Serial.println("OLED display set to 'Wi-Fi Failed'");
    }
    return;
  }

  Serial.println("Connected to Wi-Fi");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("RSSI: ");
  Serial.println(WiFi.RSSI());

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  Serial.print("Connecting to MQTT server: ");
  Serial.println(mqtt_server);
  reconnect();

  updateTopics();
  if (oledAttached) {
    if (strcmp(entities[currentEntityIndex].domain, "light") == 0) {
      publishColor();
    }
    updateDisplay();
    Serial.println("Initial display update completed");
  }
}

void loop() {
  unsigned long now = millis();
  if (now - lastOledCheck >= oledCheckInterval) {
    bool newOledState = checkOledAttached();
    if (newOledState != oledAttached) {
      oledAttached = newOledState;
      if (oledAttached && display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS)) {
        Serial.println("OLED reattached and initialized!");
        updateDisplay();
        reconnect();
      } else if (!oledAttached) {
        Serial.println("OLED detached! Unsubscribing from topics...");
        for (int i = 0; i < numEntities; i++) {
          String subUpdateTopic = String("homeassistant/") + entities[i].domain + "/" + entities[i].entityId + "/update";
          client.unsubscribe(subUpdateTopic.c_str());
          Serial.print("Unsubscribed from: ");
          Serial.println(subUpdateTopic);
        }
      }
    }
    lastOledCheck = now;
  }

  if (!oledAttached) {
    Serial.println("Loop skipped: OLED not attached");
    delay(100);
    return;
  }

  bool isConnected = (WiFi.status() == WL_CONNECTED) && client.connected();
  if (isConnected != connected) {
    connected = isConnected;
    digitalWrite(onboardLedPin, !connected);
    Serial.print("Connection status changed: ");
    Serial.println(connected ? "Connected (Wi-Fi and MQTT)" : "Disconnected (Wi-Fi or MQTT)");
    for (int i = 0; i < numEntities; i++) {
      if (connected && !stateReceived[i]) {
        stateReceived[i] = false;
        lastRequestTime = 0;
        Serial.print("Reset state received for entity ");
        Serial.print(entities[i].entityId);
        Serial.println(" due to connection change");
      }
    }
    updateDisplay();
  }

  if (!connected) {
    Serial.println("Attempting to reconnect...");
    delay(5000);
    reconnect();
  }

  client.loop();

  if (connected && !stateReceived[currentEntityIndex]) {
    if (now - lastRequestTime >= requestInterval) {
      Serial.print("Requesting state for ");
      Serial.print(entities[currentEntityIndex].entityId);
      Serial.print(" on topic: ");
      Serial.println(topics.requestState);
      client.publish(topics.requestState.c_str(), "REQUEST");
      lastRequestTime = now;
    }
  }

  if (lastKnobActivity > 0 && millis() - lastKnobActivity >= knobIdleTimeout) {
    const Entity& entity = entities[currentEntityIndex];
    if (strcmp(entity.domain, "light") == 0) {
      if (targetBrightness[currentEntityIndex] != displayBrightness[currentEntityIndex]) {
        Serial.print("Brightness changed for ");
        Serial.print(entity.entityId);
        Serial.print(": ");
        Serial.print(displayBrightness[currentEntityIndex]);
        Serial.print(" -> ");
        Serial.println(targetBrightness[currentEntityIndex]);
        publishBrightness();
        displayBrightness[currentEntityIndex] = targetBrightness[currentEntityIndex];
      }
    } else {
      if (targetVolumeLevels[currentEntityIndex] != volumeLevels[currentEntityIndex]) {
        Serial.print("Volume changed for ");
        Serial.print(entity.entityId);
        Serial.print(": ");
        Serial.print(volumeLevels[currentEntityIndex]);
        Serial.print(" -> ");
        Serial.println(targetVolumeLevels[currentEntityIndex]);
        publishVolume();
        volumeLevels[currentEntityIndex] = targetVolumeLevels[currentEntityIndex];
      }
    }
    lastKnobActivity = 0;
    Serial.println("Knob activity timeout, changes published");
  }

  // Button and encoder push handling
  bool currentButtonState = digitalRead(buttonPin);
  bool currentPushButtonState = digitalRead(encoderPUSH);
  bool currentBackButtonState = digitalRead(backButton);
  bool currentLeftButtonState = digitalRead(leftButton);

  const Entity& entity = entities[currentEntityIndex];
  if (strcmp(entity.domain, "computer") == 0) {
    // Computer-specific controls
    if (currentPushButtonState != lastPushButtonState && currentPushButtonState == LOW) {
      // Rotary push: toggle mute or turn on if computer is off
      if (!entityStates[currentEntityIndex]) {
        // Computer is off, turn it on
        Serial.print("Computer is off, turning on via ");
        Serial.println(topics.command);
        client.publish(topics.command.c_str(), "ON");
      } else {
        // Computer is on, toggle mute
        Serial.print("Dial push detected, publishing mute command to ");
        Serial.println(topics.mute);
        client.publish(topics.mute.c_str(), "TOGGLE");
      }
      delay(50);
    }

    if (currentBackButtonState != lastBackButtonState && currentBackButtonState == LOW) {
      // Back button: toggle enforce_lock
      Serial.print("Back button press detected, toggling enforce lock via ");
      Serial.println(topics.enforceLock);
      bool currentEnforceLockState = (pcSessionState == "locked");
      client.publish(topics.enforceLock.c_str(), currentEnforceLockState ? "OFF" : "ON");
      delay(50);
    }

    // Back + rotary push: power off
    if (currentBackButtonState == LOW && currentPushButtonState == LOW) {
      // Button + dial push: power off (send as set with payload OFF)
      Serial.print("Back button + dial push detected, publishing power off command to ");
      Serial.println(topics.command);
      client.publish(topics.command.c_str(), "OFF");
      delay(50);
    }
  } else {
    // Existing controls for lights and TV
    if (currentButtonState != lastButtonState) {
      if (currentButtonState == HIGH) {
        if (strcmp(entity.domain, "light") == 0) {
          targetBrightness[currentEntityIndex] = min(255, targetBrightness[currentEntityIndex] + 10);
          Serial.print("Button press (HIGH), brightness increased for ");
          Serial.print(entity.entityId);
          Serial.print(": ");
          Serial.println(targetBrightness[currentEntityIndex]);
        } else {
          targetVolumeLevels[currentEntityIndex] = min(100, targetVolumeLevels[currentEntityIndex] + 5);
          Serial.print("Button press (HIGH), volume increased for ");
          Serial.print(entity.entityId);
          Serial.print(": ");
          Serial.println(targetVolumeLevels[currentEntityIndex]);
        }
      } else {
        if (strcmp(entity.domain, "light") == 0) {
          targetBrightness[currentEntityIndex] = max(0, targetBrightness[currentEntityIndex] - 10);
          Serial.print("Button release (LOW), brightness decreased for ");
          Serial.print(entity.entityId);
          Serial.print(": ");
          Serial.println(targetBrightness[currentEntityIndex]);
        } else {
          targetVolumeLevels[currentEntityIndex] = max(0, targetVolumeLevels[currentEntityIndex] - 5);
          Serial.print("Button release (LOW), volume decreased for ");
          Serial.print(entity.entityId);
          Serial.print(": ");
          Serial.println(targetVolumeLevels[currentEntityIndex]);
        }
      }
      lastKnobActivity = millis();
      updateDisplay();
      delay(50);
    }

    if (currentPushButtonState != lastPushButtonState && currentPushButtonState == LOW) {
      entityStates[currentEntityIndex] = !entityStates[currentEntityIndex];
      Serial.print("Dial push detected, toggling state for ");
      Serial.print(entity.entityId);
      Serial.print(" to ");
      Serial.println(entityStates[currentEntityIndex] ? "ON" : "OFF");
      toggleEntity(currentBackButtonState);
      updateDisplay();
      delay(50);
    }

    if (currentBackButtonState != lastBackButtonState && currentBackButtonState == LOW) {
      if (strcmp(entity.domain, "light") == 0 && entityStates[currentEntityIndex]) {
        colorIndices[currentEntityIndex] = (colorIndices[currentEntityIndex] - 1 + numColors) % numColors;
        Serial.print("Back button pressed, changing color for ");
        Serial.print(entity.entityId);
        Serial.print(" to ");
        Serial.println(colorNames[colorIndices[currentEntityIndex]]);
        publishColor();
      } else if (strcmp(entity.domain, "media_player") == 0 && entityStates[currentEntityIndex]) {
        currentTvSourceIndex = (currentTvSourceIndex - 1 + numTvSources) % numTvSources;
        currentTvTargetSourceIndex = currentTvSourceIndex;
        Serial.print("Back button pressed, changing source for ");
        Serial.print(entity.entityId);
        Serial.print(" to ");
        Serial.println(tvSources[currentTvSourceIndex]);
        publishSource();
      }
      updateDisplay();
      delay(50);
    }
  }

  if (currentLeftButtonState != lastLeftButtonState && currentLeftButtonState == LOW) {
    currentEntityIndex = (currentEntityIndex + 1) % numEntities;
    Serial.print("Left button pressed, switching to entity: ");
    Serial.println(entities[currentEntityIndex].entityId);
    updateTopics();
    if (connected) {
      client.unsubscribe(topics.update.c_str());
      Serial.print("Unsubscribed from update topic: ");
      Serial.println(topics.update);
      client.subscribe(topics.update.c_str());
      Serial.print("Subscribed to update topic: ");
      Serial.println(topics.update);
      stateReceived[currentEntityIndex] = false;
      lastRequestTime = 0;
    }
    updateDisplay();
    delay(50);
  }

  lastButtonState = currentButtonState;
  lastPushButtonState = currentPushButtonState;
  lastBackButtonState = currentBackButtonState;
  lastLeftButtonState = currentLeftButtonState;
}

void callback(char* topic, byte* payload, unsigned int length) {
  if (!oledAttached) {
    Serial.println("MQTT callback ignored: OLED not attached");
    return;
  }

  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("Received MQTT message on topic: ");
  Serial.print(topic);
  Serial.print(", payload: ");
  Serial.println(message);

  int entityIndex = -1;
  for (int i = 0; i < numEntities; i++) {
    String expectedUpdateTopic = String("homeassistant/") + entities[i].domain + "/" + entities[i].entityId + "/update";
    if (String(topic) == expectedUpdateTopic) {
      entityIndex = i;
      break;
    }
  }

  if (entityIndex == -1) {
    Serial.println("Unknown topic, ignoring message");
    return;
  }

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    return;
  }

  const char* entity_id = doc["entity_id"];
  if (strcmp(entity_id, entities[entityIndex].entityId) != 0) {
    Serial.println("Entity ID mismatch, ignoring message");
    return;
  }

  const char* state = doc["state"];
  if (state) {
    entityStates[entityIndex] = (strcmp(state, "on") == 0);
    Serial.print("State updated for ");
    Serial.print(entity_id);
    Serial.print(": ");
    Serial.println(entityStates[entityIndex] ? "on" : "off");
    if (entityIndex == currentEntityIndex) {
      digitalWrite(buttonLedPin, entityStates[entityIndex]);
      Serial.println("Updated button LED state");
    }
    stateReceived[entityIndex] = true;
    Serial.print("State received for ");
    Serial.println(entity_id);
  }

  const Entity& entity = entities[entityIndex];
  if (strcmp(entity.domain, "light") == 0) {
    if (doc.containsKey("brightness") && !doc["brightness"].isNull()) {
      displayBrightness[entityIndex] = doc["brightness"].as<int>();
      if (lastKnobActivity == 0) {
        targetBrightness[entityIndex] = displayBrightness[entityIndex];
      }
      Serial.print("Brightness updated for ");
      Serial.print(entity_id);
      Serial.print(": ");
      Serial.println(displayBrightness[entityIndex]);
    }
    if (doc.containsKey("hs_color") && !doc["hs_color"].isNull()) {
      float h = doc["hs_color"][0].as<float>();
      float s = doc["hs_color"][1].as<float>();
      bool matched = false;
      for (int i = 0; i < numColors; i++) {
        if (abs(colors[i][0] - h) < 5 && abs(colors[i][1] - s) < 5) {
          colorIndices[entityIndex] = i;
          matched = true;
          break;
        }
      }
      if (!matched) colorIndices[entityIndex] = 0;
      Serial.print("HS color updated for ");
      Serial.print(entity_id);
      Serial.print(": ");
      Serial.print(h);
      Serial.print(",");
      Serial.println(s);
    }
  } else if (strcmp(entity.domain, "media_player") == 0 || strcmp(entity.domain, "computer") == 0) {
    if (doc.containsKey("volume_level") && !doc["volume_level"].isNull()) {
      volumeLevels[entityIndex] = (int)(doc["volume_level"].as<float>() * 100);
      if (lastKnobActivity == 0) {
        targetVolumeLevels[entityIndex] = volumeLevels[entityIndex];
      }
      Serial.print("Volume level updated for ");
      Serial.print(entity_id);
      Serial.print(": ");
      Serial.println(volumeLevels[entityIndex]);
    }
    if (strcmp(entity.domain, "media_player") == 0 && doc.containsKey("source") && !doc["source"].isNull()) {
      const char* source = doc["source"];
      for (int i = 0; i < numTvSources; i++) {
        if (strcmp(source, tvSources[i]) == 0) {
          currentTvSourceIndex = i;
          currentTvTargetSourceIndex = -1;
          break;
        }
      }
      Serial.print("Source updated for ");
      Serial.print(entity_id);
      Serial.print(": ");
      Serial.println(source);
    }
    // computer-specific attributes
    if (strcmp(entity.domain, "computer") == 0) {
      if (doc.containsKey("activewindow") && !doc["activewindow"].isNull()) {
        pcActiveWindow = doc["activewindow"].as<String>();
        Serial.print("Active window updated for ");
        Serial.print(entity_id);
        Serial.print(": ");
        Serial.println(pcActiveWindow);
      }
      if (doc.containsKey("sessionstate") && !doc["sessionstate"].isNull()) {
        pcSessionState = doc["sessionstate"].as<String>();
        Serial.print("Session state updated for ");
        Serial.print(entity_id);
        Serial.print(": ");
        Serial.println(pcSessionState);
      }
      if (doc.containsKey("enforce_lock") && !doc["enforce_lock"].isNull()) {
        bool enforceLockState = doc["enforce_lock"].as<bool>();
        Serial.print("Enforce lock updated for ");
        Serial.print(entity_id);
        Serial.print(": ");
        Serial.println(enforceLockState ? "enabled" : "disabled");
      }
    }
  }

  if (entityIndex == currentEntityIndex) {
    updateDisplay();
    Serial.println("Display updated after MQTT callback");
  }
}

void reconnect() {
  if (!oledAttached) {
    Serial.println("Reconnect skipped: OLED not attached");
    return;
  }

  while (!client.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.println("Attempting MQTT connection...");
    String clientId = "ESP32-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("MQTT connected");
      for (int i = 0; i < numEntities; i++) {
        String subUpdateTopic = String("homeassistant/") + entities[i].domain + "/" + entities[i].entityId + "/update";
        client.subscribe(subUpdateTopic.c_str());
        Serial.print("Subscribed to: ");
        Serial.println(subUpdateTopic);
      }
    } else {
      Serial.print("MQTT connection failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      digitalWrite(onboardLedPin, HIGH);
      delay(5000);
    }
  }
}

void publishBrightness() {
  if (!oledAttached || !connected) {
    Serial.println("publishBrightness skipped: OLED not attached or not connected");
    return;
  }
  String payload = String(targetBrightness[currentEntityIndex]);
  Serial.print("Publishing brightness to ");
  Serial.print(topics.brightness);
  Serial.print(": ");
  Serial.println(payload);
  client.publish(topics.brightness.c_str(), payload.c_str());
  if (!entityStates[currentEntityIndex]) {
    entityStates[currentEntityIndex] = true;
    Serial.println("Entity state set to ON due to brightness change");
    toggleEntity(HIGH);
  }
}

void publishColor() {
  if (!oledAttached || !connected) {
    Serial.println("publishColor skipped: OLED not attached or not connected");
    return;
  }
  String payload = String(colors[colorIndices[currentEntityIndex]][0]) + "," +
                   String(colors[colorIndices[currentEntityIndex]][1]);
  Serial.print("Publishing color to ");
  Serial.print(topics.hs);
  Serial.print(": ");
  Serial.println(payload);
  client.publish(topics.hs.c_str(), payload.c_str());
  if (!entityStates[currentEntityIndex]) {
    entityStates[currentEntityIndex] = true;
    Serial.println("Entity state set to ON due to color change");
    toggleEntity(HIGH);
  }
}

void publishVolume() {
  if (!oledAttached || !connected) {
    Serial.println("publishVolume skipped: OLED not attached or not connected");
    return;
  }
  String payload = String(targetVolumeLevels[currentEntityIndex]); // Send as 0-100 for number entity
  Serial.print("Publishing volume to ");
  Serial.print(topics.volume);
  Serial.print(": ");
  Serial.println(payload);
  client.publish(topics.volume.c_str(), payload.c_str());
  if (!entityStates[currentEntityIndex]) {
    entityStates[currentEntityIndex] = true;
    Serial.println("Entity state set to ON due to volume change");
    toggleEntity(HIGH);
  }
}

void publishSource() {
  if (!oledAttached || !connected) {
    Serial.println("publishSource skipped: OLED not attached or not connected");
    return;
  }
  String payload = tvSources[currentTvSourceIndex];
  Serial.print("Publishing source to ");
  Serial.print(topics.source);
  Serial.print(": ");
  Serial.println(payload);
  client.publish(topics.source.c_str(), payload.c_str());
  if (!entityStates[currentEntityIndex]) {
    entityStates[currentEntityIndex] = true;
    Serial.println("Entity state set to ON due to source change");
    toggleEntity(HIGH);
  }
}

void toggleEntity(bool currentBackButtonState) {
  if (!oledAttached || !connected) {
    Serial.println("toggleEntity skipped: OLED not attached or not connected");
    return;
  }
  String payload = entityStates[currentEntityIndex] ? "ON" : "OFF";
  const Entity& entity = entities[currentEntityIndex];
  if (strcmp(entity.domain, "media_player") == 0 && currentBackButtonState != LOW && !entityStates[currentEntityIndex]) {
    payload = "PLAYPAUSE";
  }
  Serial.print("Publishing toggle command to ");
  Serial.print(topics.command);
  Serial.print(": ");
  Serial.println(payload);
  client.publish(topics.command.c_str(), payload.c_str());
}

void updateDisplay() {
  if (!oledAttached) {
    Serial.println("updateDisplay skipped: OLED not attached");
    return;
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  const Entity& entity = entities[currentEntityIndex];
  display.print(entity.friendlyName);
  display.setCursor(0, 20);

  if (strcmp(entity.domain, "light") == 0) {
    display.print(F("Brightness: "));
    display.print(ceil(targetBrightness[currentEntityIndex] / 255.0 * 100));
    display.println('%');
    int barWidth = map(displayBrightness[currentEntityIndex], 0, 255, 0, 100);
    display.drawRect(0, 30, 100, 10, SSD1306_WHITE);
    display.fillRect(0, 30, barWidth, 10, SSD1306_WHITE);
    display.setCursor(0, 50);
    display.print(colorNames[colorIndices[currentEntityIndex]]);
  } else if (strcmp(entity.domain, "media_player") == 0) {
    display.print(F("Volume: "));
    display.print(targetVolumeLevels[currentEntityIndex]);
    display.println('%');
    int barWidth = map(volumeLevels[currentEntityIndex], 0, 100, 0, 100);
    display.drawRect(0, 30, 100, 10, SSD1306_WHITE);
    display.fillRect(0, 30, barWidth, 10, SSD1306_WHITE);
    display.setCursor(0, 50);
    if (currentTvTargetSourceIndex != -1) {
      display.print("[");
      display.print(tvSources[currentTvTargetSourceIndex]);
      display.print("]");
    } else {
      display.print(tvSources[currentTvSourceIndex]);
    }
  } else if (strcmp(entity.domain, "computer") == 0) {
    display.print(F("Volume: "));
    display.print(targetVolumeLevels[currentEntityIndex]);
    display.println('%');
    int barWidth = map(volumeLevels[currentEntityIndex], 0, 100, 0, 100);
    display.drawRect(0, 30, 100, 10, SSD1306_WHITE);
    display.fillRect(0, 30, barWidth, 10, SSD1306_WHITE);
    display.setCursor(0, 40);
    // Truncate active window name if too long
    if (pcActiveWindow.length() > 10) {
      display.print(pcActiveWindow.substring(0, 8));
      display.print("..");
    } else {
      display.print(pcActiveWindow);
    }
    
    display.setCursor(0, 50);
    display.setTextSize(1);
    display.print(pcSessionState == "locked" ? "LOCK " : "UNLOCK ");
    
    // Check if there's enforce_lock information in the payload
    bool enforceLockActive = false;
    for (int i = 0; i < numEntities; i++) {
      if (strcmp(entities[i].domain, "computer") == 0 && 
          strcmp(entities[i].entityId, entity.entityId) == 0) {
        // This is a match, check if enforce_lock is active
        enforceLockActive = (pcSessionState == "locked");
        break;
      }
    }
    
    display.print(enforceLockActive ? "(ENFORCED)" : "");
    
    display.setCursor(0, 60);
    display.setTextSize(2);
    display.println(entityStates[currentEntityIndex] ? " ON" : " OFF");
  }
  display.display();
  Serial.print("Display updated for ");
  Serial.println(entity.entityId);
}
/*
 * ORCA Xponder — storm warnings, simulated.
 *
 * Stands in for the S-band MSS transponder ISRO is fitting to fishing vessels
 * (Nabhmitra): the satellite hop is not simulated, the terminal-to-phone link is,
 * and that link is real on the actual device too — the transponder pairs to the
 * phone app exactly like this.
 *
 * The point of the exercise is the payload. A satellite message for a boat is
 * tens of bytes, not kilobytes, so no sentence is ever transmitted: this sends a
 * type code and the phone renders and speaks the warning in the fisherman's own
 * language. One frame is 20 bytes.
 *
 * Board: any ESP32 (Arduino IDE, ESP32 core installed).
 * Serial monitor: 115200 baud, line ending "Newline".
 *
 *   c              cyclone warning, severity 3, 95 km/h
 *   c 4 120        cyclone warning, severity 4, 120 km/h
 *   c 2 60 20.26 86.69   ... with a position (latitude longitude)
 *   l              lightning warning, severity 3, 40 minutes away
 *   l 4 15         lightning, severity 4, 15 minutes away
 *   h              help
 *
 * Lightning has its own type code because it kills more Indian fishermen than
 * cyclones do — a cyclone is seen coming for days, a thunderstorm is not, and an
 * open boat has no shelter. It cost one byte value and no extra bytes: the phone
 * turns the code into a spoken sentence.
 *
 * The link runs both ways. Pressing SOS in the app writes a distress call up to
 * this terminal, which prints it here — there is no S-band transmitter on an
 * ESP32, so this serial monitor stands in for the coastguard's receiver — and
 * acknowledges it back to the phone.
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define DEVICE_NAME "ORCA-XPONDER"

/*
 * Advertised as 16-bit UUIDs, which expand to the full
 * 0000a5c1-0000-1000-8000-00805f9b34fb the phone looks for — the Bluetooth base UUID.
 *
 * This matters: an advertisement holds 31 bytes. Flags (3) plus a 128-bit UUID (18)
 * plus this name (14) is 35, so the packet overflowed and no phone could see the
 * terminal at all. As 16-bit it is 3 + 4, and the name moves to the scan response.
 */
static const uint16_t SERVICE_UUID_16 = 0xA5C1;
static const uint16_t DOWNLINK_UUID_16 = 0xA5C2;
// Boat to terminal: the distress call the phone writes here.
static const uint16_t UPLINK_UUID_16 = 0xA5C3;

// The frame, byte for byte. The phone decodes this exact layout.
static const uint8_t FRAME_MAGIC = 0xA5;
static const uint8_t FRAME_VERSION = 0x01;
static const uint8_t TYPE_CYCLONE = 0x01;
static const uint8_t TYPE_LIGHTNING = 0x02;  // value = minutes until it arrives
static const uint8_t TYPE_SOS = 0x10;
static const uint8_t TYPE_SOS_ACK = 0x11;  // this terminal has it
static const size_t FRAME_BYTES = 20;

/*
 * What the boat is reporting, in the severity byte of an SOS. The same byte
 * carries storm strength on the way down — only the type says how to read it.
 */
static const char *EMERGENCY_NAMES[] = {"", "MEDICAL EMERGENCY", "ENGINE FAILURE",
                                        "MAN OVERBOARD", "SINKING"};

// Optional: a buzzer and an LED, so the hull knows even when the phone is dead.
#define BUZZER_PIN 4
#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

// Where the boat is when nothing else is given: Digha, West Bengal.
static const double DEFAULT_LAT = 21.6266;
static const double DEFAULT_LON = 87.5074;

BLECharacteristic *downlink = nullptr;
bool phoneConnected = false;

class LinkCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server) override {
    phoneConnected = true;
    Serial.println("[link] phone connected");
  }
  void onDisconnect(BLEServer *server) override {
    phoneConnected = false;
    Serial.println("[link] phone disconnected — advertising again");
    server->startAdvertising();
  }
};

/* CRC-16/CCITT-FALSE: same polynomial and seed as the TypeScript decoder. */
uint16_t crc16(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t bit = 0; bit < 8; bit++) {
      crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

void putU16(uint8_t *out, uint16_t value) {
  out[0] = (uint8_t)(value & 0xFF);
  out[1] = (uint8_t)(value >> 8);
}

void putI32(uint8_t *out, int32_t value) {
  out[0] = (uint8_t)(value & 0xFF);
  out[1] = (uint8_t)((value >> 8) & 0xFF);
  out[2] = (uint8_t)((value >> 16) & 0xFF);
  out[3] = (uint8_t)((value >> 24) & 0xFF);
}

/* Degrees to the integer the frame carries: 1e-5 degrees is about one metre. */
int32_t degreesToFixed(double degrees) {
  return (int32_t)llround(degrees * 100000.0);
}

void buildWarningFrame(uint8_t *frame, uint8_t type, uint8_t severity, uint16_t value, double lat,
                       double lon, uint32_t epochSeconds) {
  frame[0] = FRAME_MAGIC;
  frame[1] = FRAME_VERSION;
  frame[2] = type;
  frame[3] = severity;
  putI32(&frame[4], degreesToFixed(lat));
  putI32(&frame[8], degreesToFixed(lon));
  putI32(&frame[12], (int32_t)epochSeconds);
  putU16(&frame[16], value);
  putU16(&frame[18], crc16(frame, 18));
}

void printFrameHex(const uint8_t *frame) {
  Serial.print("[frame] ");
  for (size_t i = 0; i < FRAME_BYTES; i++) {
    if (frame[i] < 0x10) Serial.print('0');
    Serial.print(frame[i], HEX);
    Serial.print(i + 1 < FRAME_BYTES ? " " : "\n");
  }
}

void sendWarning(uint8_t type, uint8_t severity, uint16_t value, double lat, double lon) {
  uint8_t frame[FRAME_BYTES];
  // No real clock on the board: seconds since boot is enough for a demo, and the
  // phone shows its own arrival time.
  buildWarningFrame(frame, type, severity, value, lat, lon, (uint32_t)(millis() / 1000));

  // The same two bytes, read differently by type — which is the whole point: a
  // second kind of warning cost nothing on the wire.
  if (type == TYPE_LIGHTNING) {
    Serial.printf("[send] lightning severity=%u in %u min at %.4f, %.4f (%u bytes)\n", severity,
                  value, lat, lon, (unsigned)FRAME_BYTES);
  } else {
    Serial.printf("[send] cyclone severity=%u wind=%u km/h at %.4f, %.4f (%u bytes)\n", severity,
                  value, lat, lon, (unsigned)FRAME_BYTES);
  }
  printFrameHex(frame);

  if (!phoneConnected || downlink == nullptr) {
    Serial.println("[send] no phone connected — open the app and connect first");
    return;
  }
  downlink->setValue(frame, FRAME_BYTES);
  downlink->notify();
  Serial.println("[send] sent over BLE");
}

int32_t getI32(const uint8_t *in) {
  return (int32_t)((uint32_t)in[0] | ((uint32_t)in[1] << 8) | ((uint32_t)in[2] << 16) |
                   ((uint32_t)in[3] << 24));
}

uint16_t getU16(const uint8_t *in) { return (uint16_t)((uint16_t)in[0] | ((uint16_t)in[1] << 8)); }

/* Noise and light, so a distress call is visible on the hardware itself. */
void alertOnBoard() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  for (int i = 0; i < 6; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(120);
    digitalWrite(LED_BUILTIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    delay(80);
  }
}

/*
 * Tell the phone the distress call arrived.
 *
 * This is all the terminal can honestly confirm: that it holds the bytes.
 * Whether a coastguard has read them is not something an ESP32 can know, so
 * nothing here claims it. Without even this the fisherman is left looking at a
 * button and hoping.
 */
void sendSosAck(const uint8_t *sos) {
  if (!phoneConnected || downlink == nullptr) {
    Serial.println("[ack ] no phone connected");
    return;
  }
  uint8_t frame[FRAME_BYTES];
  memcpy(frame, sos, FRAME_BYTES);
  frame[2] = TYPE_SOS_ACK;
  putI32(&frame[12], (int32_t)(millis() / 1000));
  putU16(&frame[18], crc16(frame, 18));
  downlink->setValue(frame, FRAME_BYTES);
  downlink->notify();
  Serial.println("[ack ] acknowledged to the phone");
}

/*
 * A distress call arriving from the boat.
 *
 * On a real terminal this is the moment the S-band transmitter fires. There is
 * no transmitter here, so the frame is decoded and printed: this serial monitor
 * is standing in for the coastguard's receiver.
 */
class UplinkCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *characteristic) override {
    String raw = characteristic->getValue();
    if (raw.length() < FRAME_BYTES) {
      Serial.printf("[recv] ignored a short frame (%u bytes)\n", (unsigned)raw.length());
      return;
    }
    const uint8_t *frame = (const uint8_t *)raw.c_str();

    if (frame[0] != FRAME_MAGIC || frame[1] != FRAME_VERSION) {
      Serial.println("[recv] ignored a frame that is not ours");
      return;
    }
    if (crc16(frame, 18) != getU16(&frame[18])) {
      Serial.println("[recv] checksum failed — frame discarded");
      return;
    }
    if (frame[2] != TYPE_SOS) {
      Serial.printf("[recv] ignored an unexpected type 0x%02X\n", frame[2]);
      return;
    }

    uint8_t emergency = frame[3];
    double lat = getI32(&frame[4]) / 100000.0;
    double lon = getI32(&frame[8]) / 100000.0;
    uint32_t sentAt = (uint32_t)getI32(&frame[12]);
    uint16_t aboard = getU16(&frame[16]);

    Serial.println();
    Serial.print("[recv] ");
    printFrameHex(frame);
    Serial.println("[SOS ] ================ DISTRESS CALL ================");
    Serial.printf("[SOS ] %s\n",
                  emergency >= 1 && emergency <= 4 ? EMERGENCY_NAMES[emergency] : "UNSPECIFIED");
    Serial.printf("[SOS ] position %.5f, %.5f\n", lat, lon);
    Serial.printf("[SOS ] %u people on board\n", aboard);
    Serial.printf("[SOS ] sent at %lu (seconds, phone clock)\n", (unsigned long)sentAt);
    Serial.println("[SOS ] >>> would transmit on S-band to the coastguard <<<");
    Serial.println("[SOS ] ===============================================");

    sendSosAck(frame);
    alertOnBoard();
  }
};

void printHelp() {
  Serial.println();
  Serial.println("ORCA Xponder — type a command and press Enter:");
  Serial.println("  c                     cyclone, severity 3, 95 km/h, at Digha");
  Serial.println("  c <sev> <wind>        e.g.  c 4 120");
  Serial.println("  c <sev> <wind> <lat> <lon>   e.g.  c 4 120 20.26 86.69");
  Serial.println("  l                     lightning, severity 3, 40 minutes away");
  Serial.println("  l <sev> <mins>        e.g.  l 4 15");
  Serial.println("  l <sev> <mins> <lat> <lon>   e.g.  l 4 15 20.26 86.69");
  Serial.println("  h                     this help");
  Serial.println();
  Serial.println("Press SOS in the app and the distress call prints here.");
  Serial.println();
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;

  char command = tolower(line.charAt(0));
  if (command == 'h') {
    printHelp();
    return;
  }
  if (command != 'c' && command != 'l') {
    Serial.printf("[input] unknown command '%s' — press h for help\n", line.c_str());
    return;
  }

  bool lightning = (command == 'l');
  uint8_t severity = 3;
  // Wind in km/h for a cyclone; minutes until it arrives for lightning. Same
  // two bytes on the wire, so only the default and the ceiling differ.
  uint16_t value = lightning ? 40 : 95;
  uint16_t ceiling = lightning ? 720 : 400;
  double lat = DEFAULT_LAT;
  double lon = DEFAULT_LON;

  int parsedSeverity = 0, parsedValue = 0;
  double parsedLat = 0, parsedLon = 0;
  int fields = sscanf(line.c_str() + 1, "%d %d %lf %lf", &parsedSeverity, &parsedValue, &parsedLat,
                      &parsedLon);
  if (fields >= 1 && parsedSeverity >= 1 && parsedSeverity <= 4) severity = (uint8_t)parsedSeverity;
  if (fields >= 2 && parsedValue > 0 && parsedValue < ceiling) value = (uint16_t)parsedValue;
  if (fields >= 4) {
    lat = parsedLat;
    lon = parsedLon;
  }

  sendWarning(lightning ? TYPE_LIGHTNING : TYPE_CYCLONE, severity, value, lat, lon);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  BLEDevice::init(DEVICE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new LinkCallbacks());

  BLEService *service = server->createService(BLEUUID(SERVICE_UUID_16));
  downlink = service->createCharacteristic(
      BLEUUID(DOWNLINK_UUID_16),
      BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
  downlink->addDescriptor(new BLE2902());

  // The other direction. Writable, and it is the phone that starts the exchange,
  // so no descriptor and no notify — only a callback.
  BLECharacteristic *uplink = service->createCharacteristic(
      BLEUUID(UPLINK_UUID_16),
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  uplink->setCallbacks(new UplinkCallbacks());

  service->start();

  // Built by hand rather than left to the defaults: the name goes in the scan
  // response so the advertisement itself stays inside its 31 bytes.
  BLEAdvertisementData advertisement;
  advertisement.setFlags(0x06);  // general discoverable, BR/EDR not supported
  advertisement.setCompleteServices(BLEUUID(SERVICE_UUID_16));

  BLEAdvertisementData scanResponse;
  scanResponse.setName(DEVICE_NAME);

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->setAdvertisementData(advertisement);
  advertising->setScanResponseData(scanResponse);
  advertising->setScanResponse(true);
  advertising->setMinPreferred(0x06);
  BLEDevice::startAdvertising();

  Serial.println();
  Serial.printf("[boot] %s advertising — service 0x%04X (0000%04x-0000-1000-8000-00805f9b34fb)\n",
                DEVICE_NAME, SERVICE_UUID_16, SERVICE_UUID_16);
  Serial.println("[boot] if the phone finds nothing: Bluetooth on, and on Android 11 or older, Location on");
  printHelp();
}

void loop() {
  if (Serial.available()) {
    handleCommand(Serial.readStringUntil('\n'));
  }
  delay(20);
}

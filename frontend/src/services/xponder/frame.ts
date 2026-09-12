/**
 * The transponder frame, byte for byte.
 *
 * A satellite message for a fishing boat is tens of bytes, not kilobytes, so no
 * sentence is ever transmitted: the terminal sends a type code and this app renders
 * and speaks the warning in the fisherman's own language. One frame is 20 bytes,
 * little-endian, and this layout is shared with firmware/esp32_xponder.
 *
 *   0  magic     0xA5
 *   1  version   0x01
 *   2  type      1 = cyclone, 2 = lightning, 16 = SOS, 17 = acknowledgement
 *   3  severity  1..4 — storm strength downlink, nature of the emergency up
 *   4  latitude  int32, degrees x 1e5
 *   8  longitude int32, degrees x 1e5
 *  12  epoch     uint32, UTC seconds
 *  16  value     uint16, read by type: wind km/h for a cyclone, minutes until
 *                it arrives for lightning, people aboard for an SOS
 *  18  crc       uint16, CRC-16/CCITT-FALSE over bytes 0..17
 *
 * The same twenty bytes carry a distress call as carry a warning: only the
 * meaning of `severity` and `value` changes with the type. Nothing had to grow
 * to make the link two-way, which is the point of sending codes and not words.
 */

export const FRAME_BYTES = 20;
export const FRAME_MAGIC = 0xa5;
export const FRAME_VERSION = 0x01;

export const XPONDER_SERVICE_UUID = '0000a5c1-0000-1000-8000-00805f9b34fb';
export const XPONDER_DOWNLINK_UUID = '0000a5c2-0000-1000-8000-00805f9b34fb';
/** Boat to terminal. Written by the phone, never notified. */
export const XPONDER_UPLINK_UUID = '0000a5c3-0000-1000-8000-00805f9b34fb';

export enum XponderMessageType {
  Cyclone = 1,
  /**
   * Lightning, with the minutes until it reaches the boat in `value`.
   *
   * Worth its own code rather than folding into the cyclone warning: lightning
   * kills more Indian fishermen than cyclones do, because a cyclone is seen
   * coming for days and a thunderstorm is not, and an open boat has no shelter
   * from it. The action it calls for is also different — not "do not go out"
   * but "come back now".
   */
  Lightning = 2,
  /** Distress, sent up from the boat. */
  Sos = 0x10,
  /**
   * The terminal confirming it has the distress call.
   *
   * This is the only confirmation the terminal can honestly give: that it holds
   * the bytes. What a coastguard has or has not read is not something an ESP32
   * can know, so nothing here claims it.
   */
  SosAck = 0x11,
}

/**
 * What is wrong, in the `severity` byte of an SOS.
 *
 * Rescue is dispatched differently for each: a medical emergency wants a doctor
 * on the line, someone in the water wants everything nearby turned around now.
 */
export enum SosEmergency {
  Medical = 1,
  EngineFailure = 2,
  ManOverboard = 3,
  Sinking = 4,
}

export interface XponderFrame {
  type: XponderMessageType;
  /** 1 advisory, 2 watch, 3 warning, 4 severe. */
  severity: number;
  latitude: number;
  longitude: number;
  /** Seconds since the terminal booted or since epoch, as the terminal reports it. */
  sentAt: number;
  /** Wind speed in km/h for a cyclone message. */
  value: number;
}

/** CRC-16/CCITT-FALSE, matching the firmware's implementation. */
export function crc16(bytes: Uint8Array, length: number = bytes.length): number {
  let crc = 0xffff;
  for (let i = 0; i < length; i += 1) {
    crc ^= bytes[i] << 8;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
    }
  }
  return crc & 0xffff;
}

/**
 * Decode one frame, or null if it is not ours.
 *
 * Returns null rather than throwing: over a radio link a malformed or truncated
 * frame is an ordinary event, and a warning must never be raised from one.
 */
export function decodeFrame(bytes: Uint8Array): XponderFrame | null {
  if (bytes.length < FRAME_BYTES) return null;
  if (bytes[0] !== FRAME_MAGIC || bytes[1] !== FRAME_VERSION) return null;

  const view = new DataView(bytes.buffer, bytes.byteOffset, FRAME_BYTES);
  const expected = view.getUint16(18, true);
  if (crc16(bytes, 18) !== expected) return null;

  return {
    type: bytes[2] as XponderMessageType,
    severity: bytes[3],
    latitude: view.getInt32(4, true) / 1e5,
    longitude: view.getInt32(8, true) / 1e5,
    sentAt: view.getUint32(12, true),
    value: view.getUint16(16, true),
  };
}

/**
 * Encode a frame.
 *
 * This is on the radio path now: a distress call is built here and written to
 * the terminal, so the encoder and the firmware's decoder have to agree exactly
 * the way the decoder and its encoder always have.
 */
export function encodeFrame(frame: XponderFrame): Uint8Array {
  const bytes = new Uint8Array(FRAME_BYTES);
  const view = new DataView(bytes.buffer);
  bytes[0] = FRAME_MAGIC;
  bytes[1] = FRAME_VERSION;
  bytes[2] = frame.type;
  bytes[3] = frame.severity;
  view.setInt32(4, Math.round(frame.latitude * 1e5), true);
  view.setInt32(8, Math.round(frame.longitude * 1e5), true);
  view.setUint32(12, frame.sentAt, true);
  view.setUint16(16, frame.value, true);
  view.setUint16(18, crc16(bytes, 18), true);
  return bytes;
}

/**
 * A distress call, ready to write to the terminal.
 *
 * `peopleAboard` is carried because rescue needs to know how many they are
 * looking for, and the field costs nothing — it is the same two bytes a cyclone
 * uses for wind speed.
 */
export function encodeSos(options: {
  emergency: SosEmergency;
  latitude: number;
  longitude: number;
  peopleAboard: number;
}): Uint8Array {
  return encodeFrame({
    type: XponderMessageType.Sos,
    severity: options.emergency,
    latitude: options.latitude,
    longitude: options.longitude,
    sentAt: Math.floor(Date.now() / 1000),
    value: options.peopleAboard,
  });
}

/** "a5 01 01 03 ..." — what the firmware prints, for checking both sides agree. */
export function frameToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join(' ');
}

export function hexToFrame(hex: string): Uint8Array {
  return new Uint8Array(hex.trim().split(/\s+/).map((part) => parseInt(part, 16)));
}

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
 *   2  type      1 = cyclone
 *   3  severity  1..4
 *   4  latitude  int32, degrees x 1e5
 *   8  longitude int32, degrees x 1e5
 *  12  epoch     uint32, UTC seconds
 *  16  value     uint16, wind km/h for a cyclone
 *  18  crc       uint16, CRC-16/CCITT-FALSE over bytes 0..17
 */

export const FRAME_BYTES = 20;
export const FRAME_MAGIC = 0xa5;
export const FRAME_VERSION = 0x01;

export const XPONDER_SERVICE_UUID = '0000a5c1-0000-1000-8000-00805f9b34fb';
export const XPONDER_DOWNLINK_UUID = '0000a5c2-0000-1000-8000-00805f9b34fb';

export enum XponderMessageType {
  Cyclone = 1,
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

/** Encode a frame — used by the mock link and by tests, never on the radio path. */
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

/** "a5 01 01 03 ..." — what the firmware prints, for checking both sides agree. */
export function frameToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join(' ');
}

export function hexToFrame(hex: string): Uint8Array {
  return new Uint8Array(hex.trim().split(/\s+/).map((part) => parseInt(part, 16)));
}

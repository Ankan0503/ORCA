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
 *   2  type      1 = cyclone, 2 = lightning, 4 = cyclone track point,
 *                16 = SOS, 17 = acknowledgement
 *   3  severity  1..4 — storm strength downlink, nature of the emergency up
 *   4  latitude  int32, degrees x 1e5
 *   8  longitude int32, degrees x 1e5
 *  12  epoch     int32, read by type — see below
 *  16  value     uint16, read by type — see below
 *  18  crc       uint16, CRC-16/CCITT-FALSE over bytes 0..17
 *
 * The same twenty bytes carry a distress call as carry a warning. Only the
 * meaning of the last two fields changes with the type, so nothing has had to
 * grow — not to make the link two-way, not to add a second kind of warning, and
 * not to carry a storm's extent or its forecast track:
 *
 *   type                 epoch                    value
 *   cyclone              sent at                  wind km/h
 *   lightning            sent at                  radius km << 8 | minutes away
 *   cyclone track point  minutes past IST midnight  index << 8 | total points
 *   SOS                  sent at                  people aboard
 *
 * A track is the one message that does not fit in a single frame, so it is sent
 * as one frame per waypoint, each carrying its own position, its forecast time
 * and where it sits in the sequence. The phone reassembles them.
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
   * Lightning: how long until it arrives, and optionally how wide the cell is.
   *
   * Worth its own code rather than folding into the cyclone warning: lightning
   * kills more Indian fishermen than cyclones do, because a cyclone is seen
   * coming for days and a thunderstorm is not, and an open boat has no shelter
   * from it. The action it calls for is also different — not "do not go out"
   * but "come back now".
   *
   * The extent is part of *this* type rather than a second "storm area" code.
   * Two codes for one phenomenon would mean two render paths for one thing and
   * an operator having to remember which one carried which number — and they
   * could disagree about the same storm. A radius of 0 simply means no extent
   * was reported: the countdown is the actionable part, and the circle refines
   * "come back now" into "come back, and go south rather than east".
   */
  Lightning = 2,
  /**
   * One waypoint of a forecast cyclone track.
   *
   * Sent one frame per point, because a track is the only message here that
   * cannot fit in twenty bytes. Each frame carries its own position, the time
   * that position is forecast for, and its index in the sequence, so the phone
   * can reassemble the track and draw it — and can say how much of it has
   * arrived when frames are lost, which over a radio link is ordinary.
   */
  CycloneTrack = 4,
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
  /**
   * Read by type: when the terminal sent it for a warning, and minutes past IST
   * midnight for a track waypoint — the time that position is forecast for.
   */
  sentAt: number;
  /** Packed; read it through the helpers below rather than directly. */
  value: number;
}

/** Minutes until lightning reaches the boat. */
export function lightningMinutes(frame: XponderFrame): number {
  return frame.value & 0xff;
}

/**
 * Radius of the lightning cell in km, or null when none was reported.
 *
 * Zero means "no extent given", not "a cell of zero size" — the countdown is
 * the actionable part and the extent is a refinement, so the difference has to
 * survive into the map rather than being drawn as a dot.
 */
export function lightningRadiusKm(frame: XponderFrame): number | null {
  const radius = (frame.value >> 8) & 0xff;
  return radius > 0 ? radius : null;
}

/** Where this waypoint sits in the track: 1-based index, and the total expected. */
export function trackPosition(frame: XponderFrame): { index: number; total: number } {
  return { index: (frame.value >> 8) & 0xff, total: frame.value & 0xff };
}

/**
 * A track waypoint's forecast time, as "14:30 IST".
 *
 * The terminal has no clock — an ESP32 knows only how long it has been powered —
 * so a track carries minutes past IST midnight rather than a date. The operator
 * types the time, the phone renders it, and neither has to pretend the board
 * knows what day it is.
 */
export function trackTimeIst(frame: XponderFrame): string {
  const minutes = ((frame.sentAt % 1440) + 1440) % 1440;
  const hh = String(Math.floor(minutes / 60)).padStart(2, '0');
  const mm = String(minutes % 60).padStart(2, '0');
  return `${hh}:${mm} IST`;
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

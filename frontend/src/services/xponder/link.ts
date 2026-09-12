/**
 * The link between the transponder and this phone.
 *
 * On a real vessel the S-band terminal receives the satellite message and hands it
 * to the phone over a short-range link; that hand-off is what this speaks to. The
 * transport is deliberately behind one interface: Bluetooth on a handset, a mock in
 * a browser, and nothing above this layer knows which it is.
 */

import { Capacitor } from '@capacitor/core';
import { BleClient, numberToUUID } from '@capacitor-community/bluetooth-le';
import {
  XPONDER_DOWNLINK_UUID,
  XPONDER_SERVICE_UUID,
  XPONDER_UPLINK_UUID,
  XponderFrame,
  XponderMessageType,
  decodeFrame,
  encodeFrame,
  frameToHex,
} from './frame';

export type FrameListener = (frame: XponderFrame) => void;
export type LinkStatus = 'idle' | 'scanning' | 'connected' | 'disconnected' | 'unavailable';
export type StatusListener = (status: LinkStatus, detail?: string) => void;

export interface XponderLink {
  readonly name: string;
  readonly connected: boolean;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  /** Send a frame up to the terminal. Throws if there is nothing to send it to. */
  send(bytes: Uint8Array): Promise<void>;
  onFrame(listener: FrameListener): () => void;
  onStatus(listener: StatusListener): () => void;
}

abstract class BaseLink implements XponderLink {
  abstract readonly name: string;
  private frameListeners = new Set<FrameListener>();
  private statusListeners = new Set<StatusListener>();
  private isConnected = false;

  abstract connect(): Promise<void>;
  abstract disconnect(): Promise<void>;
  abstract send(bytes: Uint8Array): Promise<void>;

  get connected(): boolean {
    return this.isConnected;
  }

  onFrame(listener: FrameListener): () => void {
    this.frameListeners.add(listener);
    return () => this.frameListeners.delete(listener);
  }

  onStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  protected emitFrame(frame: XponderFrame) {
    this.frameListeners.forEach((listener) => listener(frame));
  }

  protected emitStatus(status: LinkStatus, detail?: string) {
    // Tracked here rather than in each subclass so `connected` cannot drift out
    // of step with what listeners were last told.
    this.isConnected = status === 'connected';
    this.statusListeners.forEach((listener) => listener(status, detail));
  }
}

/** The real thing: the ESP32 terminal, or the transponder itself, over Bluetooth. */
export class BleXponderLink extends BaseLink {
  readonly name = 'Bluetooth';
  private deviceId: string | null = null;

  async connect(): Promise<void> {
    this.emitStatus('scanning');
    try {
      await BleClient.initialize({ androidNeverForLocation: true });
      // Filtered by name, not by service: a service UUID is only matchable if it fits
      // in the advertisement, and the name is what the terminal always broadcasts.
      // The service still has to be listed so the connection may use it.
      const device = await BleClient.requestDevice({
        namePrefix: 'ORCA',
        optionalServices: [XPONDER_SERVICE_UUID],
      });
      this.deviceId = device.deviceId;

      await BleClient.connect(device.deviceId, () => {
        this.deviceId = null;
        this.emitStatus('disconnected');
      });

      await BleClient.startNotifications(
        device.deviceId,
        XPONDER_SERVICE_UUID,
        XPONDER_DOWNLINK_UUID,
        (value) => {
          const frame = decodeFrame(new Uint8Array(value.buffer));
          // A malformed frame over a radio link is ordinary; never raise a warning from one.
          if (frame) this.emitFrame(frame);
        },
      );

      this.emitStatus('connected', device.name ?? 'ORCA-XPONDER');
    } catch (error) {
      this.deviceId = null;
      this.emitStatus('unavailable', error instanceof Error ? error.message : String(error));
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (!this.deviceId) return;
    try {
      await BleClient.stopNotifications(this.deviceId, XPONDER_SERVICE_UUID, XPONDER_DOWNLINK_UUID);
      await BleClient.disconnect(this.deviceId);
    } finally {
      this.deviceId = null;
      this.emitStatus('disconnected');
    }
  }

  /**
   * Write a frame to the terminal's uplink.
   *
   * `write`, not `writeWithoutResponse`: a distress call is the one message that
   * must not be dropped silently, and the acknowledgement the terminal sends
   * back afterwards is what the fisherman actually sees.
   */
  async send(bytes: Uint8Array): Promise<void> {
    if (!this.deviceId) throw new Error('No terminal connected');
    await BleClient.write(
      this.deviceId,
      XPONDER_SERVICE_UUID,
      XPONDER_UPLINK_UUID,
      new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength),
    );
  }
}

/**
 * A terminal that is not there: the same bytes, built in the browser.
 *
 * This exists so the warning path can be demonstrated and tested without hardware —
 * the frame it emits goes through the same decoder as a real one.
 */
export class MockXponderLink extends BaseLink {
  readonly name = 'Simulated';

  async connect(): Promise<void> {
    this.emitStatus('connected', 'simulated terminal');
  }

  async disconnect(): Promise<void> {
    this.emitStatus('disconnected');
  }

  /**
   * Stand in for the terminal receiving a distress call.
   *
   * The bytes are decoded and logged exactly as the firmware logs them, then
   * acknowledged after a short delay — so the SOS screen can be exercised, and
   * its "waiting for the terminal" state actually seen, without hardware.
   */
  async send(bytes: Uint8Array): Promise<void> {
    const sent = decodeFrame(bytes);
    if (!sent) throw new Error('Refused to send a malformed frame');
    console.info('[xponder:simulated] received', frameToHex(bytes), sent);

    // Acknowledged after a short delay, so the screen's "waiting for the
    // terminal" state can actually be seen rather than flashing past.
    window.setTimeout(() => {
      const frame = decodeFrame(
        encodeFrame({
          type: XponderMessageType.SosAck,
          severity: sent.severity,
          latitude: sent.latitude,
          longitude: sent.longitude,
          sentAt: Math.floor(Date.now() / 1000),
          value: sent.value,
        }),
      );
      if (frame) this.emitFrame(frame);
    }, 900);
  }

  /** Send a cyclone warning as the terminal would, bytes and all. */
  sendCyclone(options: { severity?: number; windKmh?: number; latitude?: number; longitude?: number } = {}) {
    this.emit(XponderMessageType.Cyclone, options.severity ?? 3, options.windKmh ?? 95, options);
  }

  /** Send a lightning warning; `minutes` is how long until it reaches the boat. */
  sendLightning(options: { severity?: number; minutes?: number; latitude?: number; longitude?: number } = {}) {
    this.emit(XponderMessageType.Lightning, options.severity ?? 3, options.minutes ?? 40, options);
  }

  private emit(
    type: XponderMessageType,
    severity: number,
    value: number,
    where: { latitude?: number; longitude?: number },
  ) {
    const bytes = encodeFrame({
      type,
      severity,
      latitude: where.latitude ?? 21.6266,
      longitude: where.longitude ?? 87.5074,
      sentAt: Math.floor(Date.now() / 1000),
      value,
    });

    // Put through the real decoder, so the simulator cannot emit anything the
    // hardware path would have rejected.
    const frame = decodeFrame(bytes);
    if (frame) this.emitFrame(frame);
  }
}

/**
 * Bluetooth on a handset, the simulator anywhere else.
 *
 * Asked of Capacitor, not of `navigator.bluetooth`: the Android WebView has no Web
 * Bluetooth at all, so that test would pick the simulator on the one device where
 * the real link works.
 */
export function createXponderLink(): XponderLink {
  return Capacitor.isNativePlatform() ? new BleXponderLink() : new MockXponderLink();
}

/**
 * The one link the whole app shares.
 *
 * The warning overlay and the SOS screen both need the terminal, and a radio
 * can only be paired once — two links would mean the screen that did not open
 * the connection could never send on it. Created lazily so nothing touches
 * Bluetooth until something actually wants it.
 */
let shared: XponderLink | null = null;

export function getXponderLink(): XponderLink {
  if (!shared) shared = createXponderLink();
  return shared;
}

export { numberToUUID };

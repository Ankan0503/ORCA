import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Which way the boat's nose is pointing, from the phone's magnetometer.
 *
 * The compass is the primary instrument here, not a fallback for GPS. The
 * moment that decides whether this feature is worth building is a boat stopped
 * in open water needing to come about with no landmark in sight — and a
 * stationary GPS reports no bearing at all, because bearing is derived from
 * movement between fixes. The compass points the nose whether or not the boat
 * is moving; GPS only confirms the track once it is.
 *
 * Three things this has to be honest about, and they shape the whole API:
 *
 * 1. **It is a secure-context sensor.** Over plain `http://192.168.x.x` the
 *    events never fire, silently. Inside the Capacitor app and over HTTPS they
 *    do. `supported` distinguishes "this device has no magnetometer" from "the
 *    page is not allowed to read it", because the fixes are different.
 * 2. **iOS requires a tap.** `DeviceOrientationEvent.requestPermission` must be
 *    called from a user gesture, so the hook exposes `request()` rather than
 *    asking on mount, where it would be refused.
 * 3. **It is not precise.** A phone magnetometer is good to roughly ±5° in
 *    clean air and much worse near an engine block, a steel hull or a speaker
 *    magnet. The hook reports `accuracyDeg` and the UI draws a band that wide.
 *    Printing "95.0°" would be a lie told to three significant figures.
 *
 * Magnetic versus true north is deliberately not corrected. Declination along
 * the Indian coast runs about 0-2°, which is inside the sensor's own error, so
 * a correction would add arithmetic and no accuracy. iOS reports true north
 * already; Android reports magnetic. Both are within the band either way.
 */

export type CompassPermission = 'unknown' | 'granted' | 'denied' | 'unnecessary';

export interface CompassReading {
  /** Degrees clockwise from north, 0-360, or null when nothing is arriving. */
  headingDeg: number | null;
  /** Half-width of the band the true heading is somewhere inside. */
  accuracyDeg: number;
  /** False when the device or the page cannot read a magnetometer at all. */
  supported: boolean;
  permission: CompassPermission;
  /** True once at least one reading has arrived. */
  live: boolean;
  /** Ask iOS for permission. Must be called from a tap. */
  request: () => Promise<void>;
}

/** Default band when the platform tells us nothing about accuracy. */
const ASSUMED_ACCURACY_DEG = 12;

/** Smoothing, on the circle. A raw magnetometer jitters several degrees. */
const SMOOTHING = 0.25;

interface IosOrientationEvent extends DeviceOrientationEvent {
  webkitCompassHeading?: number;
  webkitCompassAccuracy?: number;
}

type PermissionCapableCtor = {
  requestPermission?: () => Promise<'granted' | 'denied'>;
};

/** Blend two bearings without the 359°→1° jump tearing the average apart. */
const blendBearings = (previous: number, next: number, weight: number): number => {
  let delta = ((next - previous + 540) % 360) - 180;
  return (previous + delta * weight + 360) % 360;
};

export function useCompassHeading(enabled: boolean): CompassReading {
  const [headingDeg, setHeadingDeg] = useState<number | null>(null);
  const [accuracyDeg, setAccuracyDeg] = useState<number>(ASSUMED_ACCURACY_DEG);
  const [supported, setSupported] = useState<boolean>(true);
  const [permission, setPermission] = useState<CompassPermission>('unknown');
  const smoothed = useRef<number | null>(null);

  const request = useCallback(async () => {
    const ctor = (
      typeof DeviceOrientationEvent !== 'undefined' ? DeviceOrientationEvent : undefined
    ) as unknown as PermissionCapableCtor | undefined;

    if (!ctor) {
      setSupported(false);
      return;
    }
    if (typeof ctor.requestPermission !== 'function') {
      // Android and desktop: nothing to ask for.
      setPermission('unnecessary');
      return;
    }
    try {
      const result = await ctor.requestPermission();
      setPermission(result === 'granted' ? 'granted' : 'denied');
    } catch {
      // Thrown when not called from a gesture, and on a non-secure origin.
      setPermission('denied');
    }
  }, []);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;
    if (typeof DeviceOrientationEvent === 'undefined') {
      setSupported(false);
      return;
    }

    const handle = (event: DeviceOrientationEvent) => {
      const ios = event as IosOrientationEvent;
      let heading: number | null = null;

      if (typeof ios.webkitCompassHeading === 'number') {
        // iOS: already degrees clockwise from *true* north.
        heading = ios.webkitCompassHeading;
        if (typeof ios.webkitCompassAccuracy === 'number' && ios.webkitCompassAccuracy > 0) {
          setAccuracyDeg(Math.max(5, ios.webkitCompassAccuracy));
        }
      } else if (typeof event.alpha === 'number') {
        // Android: alpha counts anticlockwise from north, so it is subtracted.
        // Without `absolute` the value is relative to wherever the page began,
        // which would be a heading that means nothing.
        if (event.absolute === false) return;
        heading = (360 - event.alpha) % 360;
      }

      if (heading == null || Number.isNaN(heading)) return;
      smoothed.current =
        smoothed.current == null ? heading : blendBearings(smoothed.current, heading, SMOOTHING);
      setHeadingDeg(smoothed.current);
    };

    // `deviceorientationabsolute` is the one that is actually north-referenced
    // on Android; plain `deviceorientation` there is relative to the starting
    // attitude and would point confidently in the wrong direction.
    const absoluteSupported = 'ondeviceorientationabsolute' in window;
    const eventName = absoluteSupported ? 'deviceorientationabsolute' : 'deviceorientation';
    window.addEventListener(eventName, handle as EventListener);

    return () => window.removeEventListener(eventName, handle as EventListener);
  }, [enabled]);

  return {
    headingDeg,
    accuracyDeg,
    supported,
    permission,
    live: headingDeg != null,
    request,
  };
}

/** Signed smallest angle from `from` to `to`, in degrees: negative is to port. */
export function bearingDelta(from: number, to: number): number {
  return ((to - from + 540) % 360) - 180;
}

/** Great-circle bearing between two positions, for the GPS track check. */
export function bearingBetween(
  fromLat: number,
  fromLon: number,
  toLat: number,
  toLon: number,
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLon = toRad(toLon - fromLon);
  const y = Math.sin(dLon) * Math.cos(toRad(toLat));
  const x =
    Math.cos(toRad(fromLat)) * Math.sin(toRad(toLat)) -
    Math.sin(toRad(fromLat)) * Math.cos(toRad(toLat)) * Math.cos(dLon);
  return (((Math.atan2(y, x) * 180) / Math.PI) + 360) % 360;
}

export const COMPASS_POINTS = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
];

export const compassPoint = (deg: number): string =>
  COMPASS_POINTS[Math.round(((deg % 360) + 360) % 360 / 22.5) % 16];

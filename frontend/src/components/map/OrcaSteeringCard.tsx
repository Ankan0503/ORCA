import React, { useEffect, useRef, useState } from 'react';
import { Compass, Volume2, VolumeX, X } from 'lucide-react';
import { RouteLeg, speak } from '../../services/orcaApi';
import {
  bearingDelta,
  compassPoint,
  useCompassHeading,
} from '../../hooks/useCompassHeading';

/**
 * The heading, as an instrument rather than a number.
 *
 * The route card already says "steer 152° SE". That is the right answer and the
 * wrong form: at the helm it means reading a number off a phone, looking at a
 * physical compass, and aligning by hand on a rolling deck, one-handed, in
 * spray. This turns the same number into something that can be flown — a
 * corridor that goes green when the nose is on course, with the correction
 * spoken aloud so it does not need to be watched at all.
 *
 * Four decisions, each of which is the difference between an instrument and a
 * decoration:
 *
 * **A band, not a hairline.** The phone's magnetometer is good to roughly ±5°
 * in clean air and much worse beside an engine. The target is drawn as a zone
 * that wide, and the readout says "about 150°", because "152.4°" would be a
 * lie told to four significant figures and would have the helmsman chasing
 * sensor noise.
 *
 * **Spoken, in the user's own language.** A captain cannot watch a screen.
 * Sarvam already speaks every other answer in ORCA; the cues use the same path.
 * They fire only when the state actually changes, and no more than once every
 * eight seconds, because an instrument that talks constantly gets muted and
 * then it is worth nothing.
 *
 * **Haptic on alignment.** One short buzz when the corridor goes green, so the
 * moment can be felt with the phone in a pocket.
 *
 * **Drift is measured, not modelled.** Where GPS is moving, the difference
 * between where the nose points and where the boat is actually going *is* the
 * set of the current — an independent check on the modelled current ORCA draws
 * on the map, which its own supplier warns is not fit for coastal navigation.
 */

/** Inside this, the corridor is green. Chosen to sit outside sensor noise. */
const ON_COURSE_DEG = 8;
/** Beyond this, badly off — a different instruction, not a louder one. */
const OFF_COURSE_DEG = 30;

/** Spoken cues no oftener than this. An instrument that nags gets muted. */
const SPEAK_INTERVAL_MS = 8000;

type Alignment = 'on' | 'drifting' | 'off';

const alignmentOf = (delta: number): Alignment => {
  const size = Math.abs(delta);
  if (size <= ON_COURSE_DEG) return 'on';
  if (size <= OFF_COURSE_DEG) return 'drifting';
  return 'off';
};

const STYLE: Record<Alignment, { color: string; bg: string; border: string; label: string }> = {
  on: { color: '#15803D', bg: '#F0FDF4', border: '#86EFAC', label: 'Hold this' },
  drifting: { color: '#A16207', bg: '#FFFBEB', border: '#FCD34D', label: 'Coming off course' },
  off: { color: '#B91C1C', bg: '#FEF2F2', border: '#FCA5A5', label: 'Well off course' },
};

/** What to say, in plain words a helmsman can act on without looking. */
const instructionFor = (delta: number, alignment: Alignment): string => {
  if (alignment === 'on') return 'Hold this course';
  const side = delta > 0 ? 'right' : 'left';
  const size = Math.abs(delta);
  if (size > OFF_COURSE_DEG) return `Turn ${side} — well off course`;
  return `Turn ${side} a little`;
};

const RIBBON_W = 300;
const RIBBON_H = 64;
/** Degrees visible across the ribbon. Wide enough to see a turn coming. */
const RIBBON_SPAN = 90;

interface OrcaSteeringCardProps {
  leg: RouteLeg;
  /**
   * Bearing the GPS track is actually making good, or null when the boat has
   * not moved far enough to have one. The page computes it, because it is the
   * page that holds consecutive fixes.
   */
  trackBearingDeg: number | null;
  language: string;
  onClose: () => void;
}

export const OrcaSteeringCard: React.FC<OrcaSteeringCardProps> = ({
  leg,
  trackBearingDeg,
  language,
  onClose,
}) => {
  const compass = useCompassHeading(true);
  const [voice, setVoice] = useState<boolean>(true);
  const lastSpoken = useRef<{ alignment: Alignment | null; at: number }>({
    alignment: null,
    at: 0,
  });
  const wasOnCourse = useRef<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const target = leg.headingDeg;
  const heading = compass.headingDeg;
  const delta = heading == null ? null : bearingDelta(heading, target);
  const alignment = delta == null ? null : alignmentOf(delta);

  // One buzz the moment the corridor goes green, so it can be felt.
  useEffect(() => {
    if (alignment == null) return;
    const onCourse = alignment === 'on';
    if (onCourse && !wasOnCourse.current) {
      navigator.vibrate?.(60);
    }
    wasOnCourse.current = onCourse;
  }, [alignment]);

  // Spoken cue, on a state change and no oftener than the interval.
  useEffect(() => {
    if (!voice || alignment == null || delta == null) return;
    const now = Date.now();
    if (alignment === lastSpoken.current.alignment) return;
    if (now - lastSpoken.current.at < SPEAK_INTERVAL_MS) return;

    lastSpoken.current = { alignment, at: now };
    let cancelled = false;

    speak(instructionFor(delta, alignment), language)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        audioRef.current?.pause();
        const audio = new Audio(url);
        audioRef.current = audio;
        // Released on the next cue, so a long trip does not leak one blob per
        // correction.
        audio.onended = () => URL.revokeObjectURL(url);
        void audio.play().catch(() => URL.revokeObjectURL(url));
      })
      .catch(() => {
        /* A failed cue is silent; the ribbon is still there to look at. */
      });

    return () => {
      cancelled = true;
    };
  }, [alignment, delta, voice, language]);

  useEffect(
    () => () => {
      audioRef.current?.pause();
    },
    [],
  );

  const style = alignment ? STYLE[alignment] : STYLE.drifting;

  // Where the target sits on the ribbon, and how wide the band is.
  const pxPerDeg = RIBBON_W / RIBBON_SPAN;
  const targetX = RIBBON_W / 2 + (delta ?? 0) * pxPerDeg;
  const bandHalf = Math.max(compass.accuracyDeg, ON_COURSE_DEG) * pxPerDeg;

  // The drift the GPS actually measures against where the nose points.
  const drift =
    heading != null && trackBearingDeg != null ? bearingDelta(heading, trackBearingDeg) : null;

  return (
    <section
      className="absolute left-2.5 right-2.5 sm:left-4 sm:right-4 bottom-[92px] sm:bottom-[104px] z-40 pointer-events-auto"
      aria-label="Steering guidance"
      id="orca-steering-card"
    >
      <div
        className="backdrop-blur-md border rounded-2xl shadow-lg p-3 flex flex-col gap-2.5"
        style={{ background: style.bg, borderColor: style.border }}
      >
        <div className="flex items-center justify-between gap-2">
          <h3
            className="font-ui font-bold text-[15px] flex items-center gap-1.5"
            style={{ color: style.color }}
          >
            <Compass size={16} />
            Steering
          </h3>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setVoice(!voice)}
              aria-pressed={voice}
              aria-label={voice ? 'Turn spoken cues off' : 'Turn spoken cues on'}
              className="p-1.5 rounded-lg text-[#557186] hover:bg-white/60"
            >
              {voice ? <Volume2 size={15} /> : <VolumeX size={15} />}
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close steering guidance"
              className="p-1.5 rounded-lg text-[#557186] hover:bg-white/60"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* The compass is a secure-context sensor, and iOS needs a tap. Both
            failures are silent, so both are said out loud. */}
        {!compass.supported && (
          <p className="font-ui text-[12.5px] text-[#B91C1C] leading-[1.45]">
            This device reports no compass, so the nose direction cannot be shown. The heading
            to steer is <b>{target}° {leg.headingCompass}</b> — set it on a hand compass.
          </p>
        )}

        {compass.supported && compass.permission === 'denied' && (
          <p className="font-ui text-[12.5px] text-[#B45309] leading-[1.45]">
            Compass access was refused. Steer <b>{target}° {leg.headingCompass}</b> by hand.
          </p>
        )}

        {compass.supported && !compass.live && compass.permission !== 'denied' && (
          <button
            type="button"
            onClick={compass.request}
            className="w-full font-ui font-bold text-[13px] py-2.5 rounded-xl bg-[#0B4A34] text-white"
          >
            Turn the compass on
          </button>
        )}

        {compass.live && delta != null && alignment != null && (
          <>
            {/* The corridor. The band is as wide as the sensor's own error. */}
            <svg
              width="100%"
              viewBox={`0 0 ${RIBBON_W} ${RIBBON_H}`}
              role="img"
              aria-label={`${instructionFor(delta, alignment)}. Off course by ${Math.round(
                Math.abs(delta),
              )} degrees.`}
            >
              <rect
                x={0}
                y={18}
                width={RIBBON_W}
                height={26}
                rx={13}
                fill="#ffffff"
                opacity={0.75}
              />
              {/* Where the course lies, as a zone rather than a line. */}
              <rect
                x={targetX - bandHalf}
                y={18}
                width={bandHalf * 2}
                height={26}
                rx={13}
                fill={style.color}
                opacity={0.22}
              />
              {/* Tick marks every 15°, so a turn has a sense of scale. */}
              {[-45, -30, -15, 0, 15, 30, 45].map((tick) => (
                <line
                  key={tick}
                  x1={RIBBON_W / 2 + tick * pxPerDeg}
                  x2={RIBBON_W / 2 + tick * pxPerDeg}
                  y1={20}
                  y2={42}
                  stroke="#CBD5E1"
                  strokeWidth={tick === 0 ? 0 : 1}
                />
              ))}
              {/* The nose: fixed in the centre, because the boat is the frame
                  of reference the helmsman is sitting in. */}
              <polygon
                points={`${RIBBON_W / 2},10 ${RIBBON_W / 2 - 8},26 ${RIBBON_W / 2 + 8},26`}
                fill={style.color}
              />
              <line
                x1={RIBBON_W / 2}
                x2={RIBBON_W / 2}
                y1={18}
                y2={44}
                stroke={style.color}
                strokeWidth={2.5}
              />
              <text
                x={RIBBON_W / 2}
                y={58}
                textAnchor="middle"
                fontSize={11}
                fontWeight={700}
                fill={style.color}
              >
                {instructionFor(delta, alignment)}
              </text>
            </svg>

            <div className="flex items-baseline justify-between gap-2">
              <span className="font-ui text-[12.5px]" style={{ color: style.color }}>
                <b>{style.label}</b>
                {/* Dead on course has no side to it; "0 degrees left" is noise. */}
                {Math.round(Math.abs(delta)) > 0 && (
                  <>
                    {' · '}
                    {Math.round(Math.abs(delta))}° {delta > 0 ? 'right' : 'left'}
                  </>
                )}
              </span>
              {/* "About", and rounded to 5°, because the sensor cannot honestly
                  support anything finer. */}
              <span className="font-ui text-[12px] text-[#557186]">
                nose about {Math.round((compass.headingDeg ?? 0) / 5) * 5}°{' '}
                {compassPoint(compass.headingDeg ?? 0)}
              </span>
            </div>
          </>
        )}

        <div className="flex items-baseline justify-between gap-2 pt-0.5 border-t border-white/70">
          <span className="font-ui text-[12px] text-[#274A62]">
            Course to steer <b>{target}° {leg.headingCompass}</b>
          </span>
          {drift != null && Math.abs(drift) >= 3 && (
            <span className="font-ui text-[11.5px] text-[#0F766E]">
              set {Math.round(Math.abs(drift))}° {drift > 0 ? 'right' : 'left'} of the nose
            </span>
          )}
        </div>

        <p className="font-ui text-[10.5px] text-[#7A8894] leading-[1.4]">
          A phone compass is good to about ±{Math.round(compass.accuracyDeg)}°, and worse near
          an engine or a steel hull — the green zone is that wide on purpose. Keep it away from
          metal and swing it in a figure of eight if it drifts.
          {drift != null && Math.abs(drift) >= 3
            ? ' The set shown is measured from your own track, not modelled.'
            : ''}
        </p>
      </div>
    </section>
  );
};

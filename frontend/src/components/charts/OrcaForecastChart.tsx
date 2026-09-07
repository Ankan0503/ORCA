import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Zap } from 'lucide-react';
import { ForecastTimeline, TimelineHour, TimelineThreshold } from '../../services/orcaApi';

/**
 * The 48-hour wave and wind forecast, drawn against India's own warning levels.
 *
 * The problem statement asks for charts alongside maps, and this is the one
 * chart that changes a decision. Everywhere else ORCA says "safe until 10:00",
 * which a fisherman has to take on trust. Here the line and the government
 * threshold are on the same axis, so he can see how much margin he has, whether
 * it is closing, and how fast.
 *
 * Three decisions worth stating, because they are what make it honest rather
 * than decorative:
 *
 * 1. The y-axis always includes the danger threshold, even on a flat calm day
 *    when the data would fit in a tenth of it. A chart auto-scaled to a 0.9 m
 *    sea makes gentle swell look alarming; keeping INCOIS's 2.0 m line in frame
 *    shows the truth, which is that there is a lot of room.
 * 2. The threshold lines carry their source in the footer — IMD's wind ladder,
 *    INCOIS's High Wave Alert. A red line at 2.0 m with no attribution would be
 *    ORCA inventing authority, which is the thing this project keeps removing.
 * 3. The caution lines are labelled as ORCA's own approach warnings, because
 *    they are. Only the danger lines are government rulings.
 *
 * Drawn by hand in SVG rather than with a charting library: the bundle is
 * already 800 KB, none of the libraries draw a threshold band the way this
 * needs, and the whole thing is about 200 lines of arithmetic.
 */

type MetricId = 'wave' | 'wind';

const PANEL_HEIGHT = 132;
const PAD_LEFT = 34;
const PAD_RIGHT = 12;
const PAD_TOP = 14;
const PAD_BOTTOM = 22;

/** Hours shown either side of now: a little history, then the useful future. */
const HOURS_BEHIND = 3;
const HOURS_AHEAD = 48;

const COLORS = {
  ink: '#062A43',
  muted: '#557186',
  grid: '#E3EDF4',
  wave: '#0C87BF',
  wind: '#0F766E',
  gust: '#94A3B8',
  danger: '#DC2626',
  caution: '#D97706',
  night: '#0F172A',
};

interface Series {
  /** The value plotted as the solid line, one per visible hour. */
  primary: (number | null)[];
  /** An optional lighter companion line — gusts under the wind trace. */
  secondary?: (number | null)[];
  secondaryLabel?: string;
  color: string;
  threshold: TimelineThreshold;
}

/** Round a domain maximum up to something a human would choose for a tick. */
const niceMax = (value: number): number => {
  if (value <= 1) return Math.ceil(value * 10) / 10;
  if (value <= 3) return Math.ceil(value * 2) / 2;
  if (value <= 10) return Math.ceil(value);
  return Math.ceil(value / 5) * 5;
};

const hourLabel = (iso: string): string => iso.slice(11, 16);

/** Build an SVG path, breaking the line wherever the forecast has a gap. */
const buildPath = (
  values: (number | null)[],
  x: (i: number) => number,
  y: (v: number) => number,
): string => {
  let path = '';
  let pen = false;
  values.forEach((value, index) => {
    if (value == null) {
      pen = false;
      return;
    }
    path += `${pen ? 'L' : 'M'}${x(index).toFixed(1)},${y(value).toFixed(1)}`;
    pen = true;
  });
  return path;
};

interface PanelProps {
  title: string;
  series: Series;
  hours: TimelineHour[];
  width: number;
  nowIndex: number;
  safeUntilIndex: number | null;
  nights: [number, number][];
  active: number | null;
  onActive: (index: number | null) => void;
}

const Panel: React.FC<PanelProps> = ({
  title,
  series,
  hours,
  width,
  nowIndex,
  safeUntilIndex,
  nights,
  active,
  onActive,
}) => {
  const { threshold } = series;
  const plotW = Math.max(40, width - PAD_LEFT - PAD_RIGHT);
  const plotH = PANEL_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const observed = [...series.primary, ...(series.secondary ?? [])].filter(
    (v): v is number => v != null,
  );
  // The danger line is always in frame — see the note at the top of the file.
  const domainMax = niceMax(
    Math.max(threshold.danger * 1.25, observed.length ? Math.max(...observed) * 1.15 : 0, 0.1),
  );

  const x = (i: number) =>
    PAD_LEFT + (hours.length <= 1 ? 0 : (i / (hours.length - 1)) * plotW);
  const y = (v: number) => PAD_TOP + plotH - (Math.min(v, domainMax) / domainMax) * plotH;

  const linePath = buildPath(series.primary, x, y);
  const areaPath = linePath
    ? `${linePath}L${x(hours.length - 1).toFixed(1)},${(PAD_TOP + plotH).toFixed(1)}L${x(0).toFixed(
        1,
      )},${(PAD_TOP + plotH).toFixed(1)}Z`
    : '';
  const gradientId = `orca-fill-${title.replace(/\s+/g, '')}`;

  const ticks = [0, domainMax / 2, domainMax];

  return (
    <svg
      width={width}
      height={PANEL_HEIGHT}
      role="img"
      aria-label={`${title} forecast against the ${threshold.dangerLabel} level`}
      style={{ touchAction: 'pan-y' }}
      onPointerMove={(e) => {
        const box = e.currentTarget.getBoundingClientRect();
        const ratio = (e.clientX - box.left - PAD_LEFT) / plotW;
        const index = Math.round(ratio * (hours.length - 1));
        onActive(index >= 0 && index < hours.length ? index : null);
      }}
      onPointerLeave={() => onActive(null)}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={series.color} stopOpacity="0.26" />
          <stop offset="100%" stopColor={series.color} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Night, so "the wind turns at 03:00" reads as the dark hour it is. */}
      {nights.map(([from, to], i) => (
        <rect
          key={i}
          x={x(from)}
          y={PAD_TOP}
          width={Math.max(0, x(to) - x(from))}
          height={plotH}
          fill={COLORS.night}
          opacity={0.05}
        />
      ))}

      {/* Everything above the government danger level. */}
      <rect
        x={PAD_LEFT}
        y={PAD_TOP}
        width={plotW}
        height={Math.max(0, y(threshold.danger) - PAD_TOP)}
        fill={COLORS.danger}
        opacity={0.06}
      />

      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={PAD_LEFT}
            x2={PAD_LEFT + plotW}
            y1={y(t)}
            y2={y(t)}
            stroke={COLORS.grid}
            strokeWidth={1}
          />
          <text x={PAD_LEFT - 6} y={y(t) + 3.5} textAnchor="end" fontSize={9.5} fill={COLORS.muted}>
            {t % 1 === 0 ? t : t.toFixed(1)}
          </text>
        </g>
      ))}

      {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} />}

      {series.secondary && (
        <path
          d={buildPath(series.secondary, x, y)}
          fill="none"
          stroke={COLORS.gust}
          strokeWidth={1.4}
          strokeDasharray="3 3"
          strokeLinejoin="round"
        />
      )}

      {[
        { value: threshold.danger, color: COLORS.danger, label: threshold.dangerLabel },
        { value: threshold.caution, color: COLORS.caution, label: threshold.cautionLabel },
      ].map((line, i) => {
        // The two levels can sit close together on the axis — IMD's 35 km/h and
        // the 30 km/h approach warning are 5 apart on a 45 km/h scale — so the
        // lower caption drops below its line instead of colliding with the one
        // above it.
        const gap = Math.abs(y(threshold.caution) - y(threshold.danger));
        const below = i === 1 && gap < 14;
        return (
          <g key={line.label}>
            <line
              x1={PAD_LEFT}
              x2={PAD_LEFT + plotW}
              y1={y(line.value)}
              y2={y(line.value)}
              stroke={line.color}
              strokeWidth={1.3}
              strokeDasharray="5 4"
              opacity={0.9}
            />
            <text
              x={PAD_LEFT + plotW}
              y={y(line.value) + (below ? 10 : -4)}
              textAnchor="end"
              fontSize={9}
              fontWeight={700}
              fill={line.color}
            >
              {line.label} · {line.value}
              {threshold.unit}
            </text>
          </g>
        );
      })}

      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={series.color}
          strokeWidth={2.1}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}

      {/* Where the forecast stops being safe. */}
      {safeUntilIndex != null && (
        <g>
          <line
            x1={x(safeUntilIndex)}
            x2={x(safeUntilIndex)}
            y1={PAD_TOP}
            y2={PAD_TOP + plotH}
            stroke={COLORS.danger}
            strokeWidth={1.6}
          />
          <circle cx={x(safeUntilIndex)} cy={PAD_TOP} r={2.6} fill={COLORS.danger} />
        </g>
      )}

      {/* Now. */}
      <line
        x1={x(nowIndex)}
        x2={x(nowIndex)}
        y1={PAD_TOP - 4}
        y2={PAD_TOP + plotH}
        stroke={COLORS.ink}
        strokeWidth={1.2}
        strokeDasharray="2 2"
      />

      {active != null && series.primary[active] != null && (
        <g pointerEvents="none">
          <line
            x1={x(active)}
            x2={x(active)}
            y1={PAD_TOP}
            y2={PAD_TOP + plotH}
            stroke={series.color}
            strokeWidth={1}
            opacity={0.7}
          />
          <circle
            cx={x(active)}
            cy={y(series.primary[active] as number)}
            r={3.6}
            fill="#fff"
            stroke={series.color}
            strokeWidth={2}
          />
        </g>
      )}

      {/* Storm hours, marked on the baseline of every panel. */}
      {hours.map((hour, i) =>
        hour.isThunderstorm ? (
          <rect
            key={i}
            x={x(i) - 1.5}
            y={PAD_TOP + plotH - 4}
            width={3}
            height={4}
            fill="#7C3AED"
          />
        ) : null,
      )}

      <text x={PAD_LEFT} y={11} fontSize={10} fontWeight={700} fill={COLORS.ink}>
        {title} ({threshold.unit})
      </text>
    </svg>
  );
};

interface OrcaForecastChartProps {
  timeline: ForecastTimeline;
}

export const OrcaForecastChart: React.FC<OrcaForecastChartProps> = ({ timeline }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState<number | null>(null);
  const [metric, setMetric] = useState<MetricId | 'both'>('both');

  // Measured rather than assumed: a viewBox scaled to a 360 px phone would
  // shrink the axis labels to about 5 px.
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(node);
    setWidth(node.getBoundingClientRect().width);
    return () => observer.disconnect();
  }, []);

  const view = useMemo(() => {
    const all = timeline.hours;
    if (all.length === 0) return null;

    // The series is in the forecast location's local time and so is the reader,
    // so the browser clock is the right one to place "now" with.
    const times = all.map((h) => new Date(h.time).getTime());
    const now = Date.now();
    let nowIdx = times.findIndex((t) => t >= now);
    if (nowIdx === -1) nowIdx = times.length - 1;

    const from = Math.max(0, nowIdx - HOURS_BEHIND);
    const to = Math.min(all.length, nowIdx + HOURS_AHEAD + 1);
    const hours = all.slice(from, to);

    const indexOf = (iso: string | null): number | null => {
      if (!iso) return null;
      const i = hours.findIndex((h) => h.time === iso);
      return i === -1 ? null : i;
    };

    // Night bands, clipped to the visible window.
    const nights: [number, number][] = [];
    const sunsets = timeline.sun.sunset.map((s) => new Date(s).getTime());
    const sunrises = timeline.sun.sunrise.map((s) => new Date(s).getTime());
    const visible = hours.map((h) => new Date(h.time).getTime());
    sunsets.forEach((set) => {
      const rise = sunrises.find((r) => r > set);
      if (rise == null) return;
      const start = visible.findIndex((t) => t >= set);
      const end = visible.findIndex((t) => t >= rise);
      const a = start === -1 ? (visible[visible.length - 1] >= set ? 0 : null) : start;
      if (a == null) return;
      nights.push([a, end === -1 ? hours.length - 1 : end]);
    });

    return {
      hours,
      nowIndex: nowIdx - from,
      safeUntilIndex: indexOf(timeline.safeUntil),
      nights,
    };
  }, [timeline]);

  if (!view || view.hours.length === 0) {
    return null;
  }

  const { hours, nowIndex, safeUntilIndex, nights } = view;

  const waveSeries: Series = {
    primary: hours.map((h) => h.waveHeightM),
    color: COLORS.wave,
    threshold: timeline.thresholds.wave,
  };
  const windSeries: Series = {
    primary: hours.map((h) => h.windSpeedKmh),
    secondary: hours.map((h) => h.windGustsKmh),
    secondaryLabel: 'gusts',
    color: COLORS.wind,
    threshold: timeline.thresholds.wind,
  };

  const activeHour: TimelineHour | null = active != null ? hours[active] ?? null : null;
  const stormHours = hours.filter((h) => h.isThunderstorm).length;

  // Time labels: every sixth hour, so a phone shows about eight of them.
  // Every sixth hour, and nothing else. An extra label pinned to the left edge
  // printed on top of the first six-hourly tick whenever the window started a
  // few hours before midnight — the axis read "21:0000:00".
  const axisTicks = hours
    .map((h, i) => ({ h, i }))
    .filter(({ h }) => new Date(h.time).getHours() % 6 === 0);

  return (
    <section
      className="w-full flex flex-col gap-2 select-none"
      aria-label="Wave and wind forecast against government warning levels"
      id="orca-forecast-chart"
    >
      <div className="flex items-baseline justify-between px-1">
        <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight">
          Next 48 hours
        </h3>
        <div className="flex gap-1" role="group" aria-label="Choose which forecast to show">
          {(
            [
              ['both', 'Both'],
              ['wave', 'Waves'],
              ['wind', 'Wind'],
            ] as [MetricId | 'both', string][]
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setMetric(id)}
              aria-pressed={metric === id}
              className={`font-ui font-bold text-[11px] px-2 py-1 rounded-lg transition-colors ${
                metric === id
                  ? 'bg-[#062A43] text-white'
                  : 'bg-white/80 text-[#557186] border border-[#D8E6F0]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div
        ref={containerRef}
        className="w-full bg-white/95 border border-[#D8E6F0] rounded-2xl p-2 sm:p-3 overflow-hidden"
      >
        {width > 0 && (
          <>
            {(metric === 'both' || metric === 'wave') && (
              <Panel
                title="Waves"
                series={waveSeries}
                hours={hours}
                width={width - 16}
                nowIndex={nowIndex}
                safeUntilIndex={safeUntilIndex}
                nights={nights}
                active={active}
                onActive={setActive}
              />
            )}
            {(metric === 'both' || metric === 'wind') && (
              <Panel
                title="Wind"
                series={windSeries}
                hours={hours}
                width={width - 16}
                nowIndex={nowIndex}
                safeUntilIndex={safeUntilIndex}
                nights={nights}
                active={active}
                onActive={setActive}
              />
            )}

            {/* Shared time axis. */}
            <svg width={width - 16} height={16} aria-hidden="true">
              {axisTicks.map(({ h, i }) => {
                const plotW = Math.max(40, width - 16 - PAD_LEFT - PAD_RIGHT);
                const cx = PAD_LEFT + (hours.length <= 1 ? 0 : (i / (hours.length - 1)) * plotW);
                return (
                  <text
                    key={h.time}
                    x={cx}
                    y={11}
                    textAnchor={i === 0 ? 'start' : 'middle'}
                    fontSize={9.5}
                    fill={COLORS.muted}
                  >
                    {hourLabel(h.time)}
                  </text>
                );
              })}
            </svg>
          </>
        )}
      </div>

      {/* What the reader is pointing at, or the headline when they are not. */}
      <div className="w-full min-h-[46px] px-1">
        {activeHour ? (
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <span className="font-ui font-bold text-[13px] text-[#062A43]">
              {hourLabel(activeHour.time)}
            </span>
            {activeHour.waveHeightM != null && (
              <span className="font-ui text-[12.5px] text-[#0C87BF] font-semibold">
                {activeHour.waveHeightM.toFixed(1)} m waves
              </span>
            )}
            {activeHour.windSpeedKmh != null && (
              <span className="font-ui text-[12.5px] text-[#0F766E] font-semibold">
                {Math.round(activeHour.windSpeedKmh)} km/h wind
                {activeHour.windGustsKmh != null &&
                  `, gusting ${Math.round(activeHour.windGustsKmh)}`}
              </span>
            )}
            {activeHour.reasons.length > 0 && (
              <span className="font-ui text-[12px] text-[#B91C1C] font-semibold w-full">
                {activeHour.reasons.join(' · ')}
              </span>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            {timeline.safeUntil ? (
              <span className="font-ui text-[12.5px] text-[#062A43] flex items-start gap-1.5">
                <AlertTriangle size={13} className="text-[#DC2626] shrink-0 mt-[3px]" />
                {/* One text node, so the sentence wraps as a sentence — as
                    separate flex children the clock time became its own
                    column and the line broke around it. */}
                <span>
                  Safe until <b>{hourLabel(timeline.safeUntil)}</b>
                  {timeline.safeUntilReasons.length > 0 &&
                    ` — then ${timeline.safeUntilReasons.join(', ')}`}
                </span>
              </span>
            ) : (
              <span className="font-ui text-[12.5px] text-[#15803D] font-semibold">
                Nothing in the next 48 hours crosses a warning level.
              </span>
            )}
            {stormHours > 0 && (
              <span className="font-ui text-[12px] text-[#6D28D9] flex items-center gap-1.5">
                <Zap size={12} className="shrink-0" />
                {stormHours} hour{stormHours === 1 ? '' : 's'} with lightning, marked on the
                baseline
              </span>
            )}
            <span className="font-ui text-[11.5px] text-[#8AA0B0] leading-[1.35]">
              Touch the chart to read an hour.
            </span>
          </div>
        )}
      </div>

      {/* Attribution. The red lines are somebody's ruling, and it is named. */}
      <p className="font-ui text-[10.5px] text-[#8AA0B0] leading-[1.4] px-1">
        Red lines are government warning levels — {timeline.thresholds.wave.source};{' '}
        {timeline.thresholds.wind.source}. Amber lines are ORCA&apos;s own earlier warning, not
        an official threshold. Forecast: {timeline.source}.
      </p>
    </section>
  );
};

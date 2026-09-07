import React, { useEffect, useMemo, useRef, useState } from 'react';
import { History, Info } from 'lucide-react';
import { SeasonTrends, TrendMetric } from '../../services/orcaApi';

/**
 * A decade of the sea at one place, one year per bar.
 *
 * This is the screen behind the problem statement's hardest question — *"why has
 * fish productivity declined?"* — and the important thing it does is refuse to
 * answer it directly. ORCA holds no catch records, so the caveat below the chart
 * is not a disclaimer bolted on afterwards; it is the honest boundary of what
 * these four measurements can support. What the reader gets instead is real:
 * the same weeks of every year since 2016, from ERA5 and NOAA's satellite
 * record, with the mechanism that links each change to the food chain.
 *
 * Bars rather than a line, because these are eleven discrete seasons, not a
 * continuous signal — a line between 2019 and 2020 would imply readings that do
 * not exist. The baseline runs across as a dashed rule so this year's bar can be
 * read against the years before it without arithmetic.
 */

const PANEL_HEIGHT = 118;
const PAD_LEFT = 34;
const PAD_RIGHT = 10;
const PAD_TOP = 10;
const PAD_BOTTOM = 20;

const COLORS = {
  ink: '#062A43',
  muted: '#557186',
  grid: '#E3EDF4',
  bar: '#7FB4D4',
  barLatest: '#0C87BF',
  baseline: '#B45309',
};

/** A short, plain reading of which way a metric has moved. */
const direction = (metric: TrendMetric): string | null => {
  if (metric.slopePerDecade == null) return null;
  const size = Math.abs(metric.slopePerDecade);
  // Below these, the line is being pulled by one unusual year rather than a
  // trend. Same thresholds the agent uses to decide what is worth saying.
  const material: Record<TrendMetric['key'], number> = {
    sst: 0.15,
    wind: 1.0,
    rain: 1.5,
    wave: 0.15,
  };
  if (size < material[metric.key]) return 'no clear trend';
  return `${metric.slopePerDecade > 0 ? '+' : '−'}${size.toFixed(2)} ${metric.unit} per decade`;
};

interface OrcaTrendChartProps {
  trends: SeasonTrends;
}

export const OrcaTrendChart: React.FC<OrcaTrendChartProps> = ({ trends }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  const [selected, setSelected] = useState<string>(trends.metrics[0]?.key ?? 'sst');

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(node);
    setWidth(node.getBoundingClientRect().width);
    return () => observer.disconnect();
  }, []);

  const metric = useMemo(
    () => trends.metrics.find((m) => m.key === selected) ?? trends.metrics[0],
    [trends.metrics, selected],
  );

  if (!metric || metric.byYear.length < 2) return null;

  const plotW = Math.max(40, width - 16 - PAD_LEFT - PAD_RIGHT);
  const plotH = PANEL_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const values = metric.byYear.map((p) => p.value);
  // The domain hugs the data rather than starting at zero: these are seasonal
  // means of temperature and wind, where the interesting movement is a fraction
  // of the absolute value and a zero baseline would flatten it into nothing.
  const lo = Math.min(...values, metric.baseline ?? Infinity);
  const hi = Math.max(...values, metric.baseline ?? -Infinity);
  const pad = (hi - lo) * 0.25 || Math.abs(hi) * 0.05 || 1;
  const domainLo = lo - pad;
  const domainHi = hi + pad;

  const y = (v: number) =>
    PAD_TOP + plotH - ((v - domainLo) / (domainHi - domainLo || 1)) * plotH;
  const barW = Math.max(4, (plotW / metric.byYear.length) * 0.62);
  const x = (i: number) =>
    PAD_LEFT + (plotW / metric.byYear.length) * (i + 0.5) - barW / 2;

  const latestYear = metric.lastYear;

  return (
    <section
      className="w-full flex flex-col gap-2 select-none"
      aria-label="How the sea here has changed over the past decade"
      id="orca-trend-chart"
    >
      {/* Stacked rather than side by side: on a 360 px phone the heading and
          the window label fought for the same line and both wrapped. */}
      <div className="flex flex-col gap-0.5 px-1">
        <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight flex items-center gap-1.5">
          <History size={16} className="text-[#0C87BF] shrink-0" />
          Has the sea changed?
        </h3>
        <span className="font-ui text-[11.5px] text-[#8AA0B0]">
          {trends.window} in each year since {Math.min(...trends.metrics.map((m) => m.firstYear ?? 9999))}
        </span>
      </div>

      <div className="flex gap-1 flex-wrap px-1" role="group" aria-label="Choose a measurement">
        {trends.metrics.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => setSelected(m.key)}
            aria-pressed={m.key === metric.key}
            className={`font-ui font-bold text-[11px] px-2 py-1 rounded-lg transition-colors ${
              m.key === metric.key
                ? 'bg-[#062A43] text-white'
                : 'bg-white/80 text-[#557186] border border-[#D8E6F0]'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div
        ref={containerRef}
        className="w-full bg-white/95 border border-[#D8E6F0] rounded-2xl p-2 sm:p-3 overflow-hidden"
      >
        {width > 0 && (
          <svg
            width={width - 16}
            height={PANEL_HEIGHT}
            role="img"
            aria-label={`${metric.label} for ${trends.window} in each year from ${metric.firstYear} to ${metric.lastYear}`}
          >
            {[domainLo, (domainLo + domainHi) / 2, domainHi].map((t) => (
              <g key={t}>
                <line
                  x1={PAD_LEFT}
                  x2={PAD_LEFT + plotW}
                  y1={y(t)}
                  y2={y(t)}
                  stroke={COLORS.grid}
                  strokeWidth={1}
                />
                <text
                  x={PAD_LEFT - 5}
                  y={y(t) + 3.5}
                  textAnchor="end"
                  fontSize={9}
                  fill={COLORS.muted}
                >
                  {t.toFixed(metric.key === 'wind' || metric.key === 'rain' ? 0 : 1)}
                </text>
              </g>
            ))}

            {metric.byYear.map((point, i) => {
              const isLatest = point.year === latestYear;
              const top = y(point.value);
              return (
                <g key={point.year}>
                  <rect
                    x={x(i)}
                    y={top}
                    width={barW}
                    height={Math.max(1, PAD_TOP + plotH - top)}
                    rx={2}
                    fill={isLatest ? COLORS.barLatest : COLORS.bar}
                  >
                    <title>{`${point.year}: ${point.value.toFixed(2)} ${metric.unit}`}</title>
                  </rect>
                  {/* Only every other year is labelled, so eleven of them fit. */}
                  {(i % 2 === 0 || isLatest) && (
                    <text
                      x={x(i) + barW / 2}
                      y={PANEL_HEIGHT - 6}
                      textAnchor="middle"
                      fontSize={8.5}
                      fontWeight={isLatest ? 700 : 400}
                      fill={isLatest ? COLORS.ink : COLORS.muted}
                    >
                      {`'${String(point.year).slice(2)}`}
                    </text>
                  )}
                </g>
              );
            })}

            {metric.baseline != null && (
              <g>
                <line
                  x1={PAD_LEFT}
                  x2={PAD_LEFT + plotW}
                  y1={y(metric.baseline)}
                  y2={y(metric.baseline)}
                  stroke={COLORS.baseline}
                  strokeWidth={1.3}
                  strokeDasharray="5 4"
                />
                <text
                  x={PAD_LEFT + plotW}
                  y={y(metric.baseline) - 4}
                  textAnchor="end"
                  fontSize={9}
                  fontWeight={700}
                  fill={COLORS.baseline}
                >
                  earlier years&apos; average
                </text>
              </g>
            )}
          </svg>
        )}
      </div>

      <div className="px-1 flex flex-col gap-1">
        <span className="font-ui text-[12.5px] text-[#062A43]">
          <b>{metric.label}</b>: {direction(metric) ?? 'not enough years to judge a trend'}
          {metric.anomaly != null && (
            <>
              {' · this year is '}
              <b>
                {metric.anomaly > 0 ? '+' : '−'}
                {Math.abs(metric.anomaly).toFixed(2)} {metric.unit}
              </b>
              {' against the earlier average'}
            </>
          )}
        </span>
        <span className="font-ui text-[11px] text-[#8AA0B0] leading-[1.4]">
          {metric.source}
        </span>
      </div>

      {/* The boundary of the claim, stated where the reader will see it. */}
      {trends.notes.map((note) => (
        <p
          key={note}
          className="font-ui text-[11.5px] text-[#5C6B76] leading-[1.45] px-1 flex items-start gap-1.5"
        >
          <Info size={12} className="shrink-0 mt-[3px] text-[#8AA0B0]" />
          <span>{note}</span>
        </p>
      ))}
    </section>
  );
};

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Database, FileText, LineChart } from 'lucide-react';
import { AgentEvidence } from '../../services/orcaApi';

/**
 * What the agents produced besides words.
 *
 * Three of ORCA's agents return something a sentence cannot carry: the
 * visualization agent returns a chart it chose, the reporting agent returns a
 * dated brief, and the data discovery agent returns the source catalogue with a
 * live reachability check. All three were being built on the server and then
 * thrown away, because the answer card only ever rendered prose.
 *
 * Everything here comes out of an agent's own `data` — nothing is recomputed in
 * the browser, and every block carries the provenance the agent attached to it.
 * A chart in particular is the most persuasive way to show something false, so
 * the source line under it is not decoration.
 */

interface ChartPoint {
  t: string;
  v: number | null;
}

interface ChartSpec {
  kind: 'forecast' | 'trend';
  title: string;
  unit: string;
  points: ChartPoint[];
  caution?: number | null;
  danger?: number | null;
  dangerLabel?: string | null;
  baseline?: number | null;
  baselineLabel?: string | null;
  source: string;
  thresholdSource?: string | null;
  markerAt?: string | null;
  markerLabel?: string | null;
  notes?: string[];
}

interface BriefSection {
  title: string;
  source: string;
  issuedAt: string | null;
  lines: string[];
}

interface BriefSpec {
  title: string;
  compiledAt: string;
  position: { latitude: number; longitude: number };
  sections: BriefSection[];
  caveats: string[];
}

interface CatalogueEntry {
  key: string;
  name: string;
  provider: string;
  usedFor: string;
  resolution: string;
  cadence: string;
  notes: string | null;
  rejected: string | null;
  coversPosition: boolean;
  reachable: boolean | null;
  latencyMs: number | null;
  detail: string | null;
}

const W = 320;
const H = 110;
const PAD_L = 30;
const PAD_R = 8;
const PAD_T = 8;
const PAD_B = 18;

const MiniChart: React.FC<{ spec: ChartSpec }> = ({ spec }) => {
  const values = spec.points.map((p) => p.v).filter((v): v is number => v != null);
  if (values.length < 2) return null;

  // A forecast keeps its warning level in frame even when the sea is flat, for
  // the same reason the full-size chart does: auto-scaling to a calm day makes
  // gentle swell fill the panel and look alarming.
  const lo = Math.min(...values, spec.kind === 'trend' ? (spec.baseline ?? Infinity) : Infinity);
  const hi = Math.max(
    ...values,
    spec.kind === 'forecast' ? (spec.danger ?? -Infinity) : (spec.baseline ?? -Infinity),
  );
  const pad = (hi - lo) * 0.2 || Math.abs(hi) * 0.05 || 1;
  const domainLo = spec.kind === 'forecast' ? Math.min(0, lo) : lo - pad;
  const domainHi = hi + pad;

  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const x = (i: number) => PAD_L + (i / Math.max(1, spec.points.length - 1)) * plotW;
  const y = (v: number) =>
    PAD_T + plotH - ((v - domainLo) / (domainHi - domainLo || 1)) * plotH;

  const markerIndex =
    spec.markerAt != null ? spec.points.findIndex((p) => p.t === spec.markerAt) : -1;

  let path = '';
  let pen = false;
  spec.points.forEach((p, i) => {
    if (p.v == null) {
      pen = false;
      return;
    }
    path += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`;
    pen = true;
  });

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={spec.title}>
      {[domainLo, domainHi].map((t) => (
        <g key={t}>
          <line x1={PAD_L} x2={W - PAD_R} y1={y(t)} y2={y(t)} stroke="#E3EDF4" strokeWidth={1} />
          <text x={PAD_L - 4} y={y(t) + 3} textAnchor="end" fontSize={8} fill="#8AA0B0">
            {t.toFixed(spec.unit === 'm' ? 1 : 0)}
          </text>
        </g>
      ))}

      {spec.kind === 'forecast' && spec.danger != null && (
        <>
          <rect
            x={PAD_L}
            y={PAD_T}
            width={plotW}
            height={Math.max(0, y(spec.danger) - PAD_T)}
            fill="#DC2626"
            opacity={0.06}
          />
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={y(spec.danger)}
            y2={y(spec.danger)}
            stroke="#DC2626"
            strokeWidth={1.1}
            strokeDasharray="4 3"
          />
          <text x={W - PAD_R} y={y(spec.danger) - 3} textAnchor="end" fontSize={7.5} fontWeight={700} fill="#DC2626">
            {spec.dangerLabel}
          </text>
        </>
      )}

      {spec.kind === 'trend' &&
        spec.points.map((p, i) =>
          p.v == null ? null : (
            <rect
              key={p.t}
              x={x(i) - (plotW / spec.points.length) * 0.3}
              y={y(p.v)}
              width={(plotW / spec.points.length) * 0.6}
              height={Math.max(1, PAD_T + plotH - y(p.v))}
              rx={1.5}
              fill={i === spec.points.length - 1 ? '#0C87BF' : '#7FB4D4'}
            />
          ),
        )}

      {spec.kind === 'trend' && spec.baseline != null && (
        <line
          x1={PAD_L}
          x2={W - PAD_R}
          y1={y(spec.baseline)}
          y2={y(spec.baseline)}
          stroke="#B45309"
          strokeWidth={1.1}
          strokeDasharray="4 3"
        />
      )}

      {spec.kind === 'forecast' && path && (
        <path d={path} fill="none" stroke="#0C87BF" strokeWidth={1.8} strokeLinejoin="round" />
      )}

      {markerIndex >= 0 && (
        <line
          x1={x(markerIndex)}
          x2={x(markerIndex)}
          y1={PAD_T}
          y2={PAD_T + plotH}
          stroke="#DC2626"
          strokeWidth={1.4}
        />
      )}

      {/* First and last labels only — there is no room for more at this size. */}
      {[0, spec.points.length - 1].map((i) => (
        <text
          key={i}
          x={x(i)}
          y={H - 5}
          textAnchor={i === 0 ? 'start' : 'end'}
          fontSize={8}
          fill="#8AA0B0"
        >
          {spec.kind === 'trend' ? spec.points[i].t : spec.points[i].t.slice(11, 16)}
        </text>
      ))}
    </svg>
  );
};

const ChartBlock: React.FC<{ spec: ChartSpec }> = ({ spec }) => (
  <section className="w-full bg-white/95 border border-[#D8E6F0] rounded-2xl p-3 flex flex-col gap-1.5">
    <h4 className="font-ui font-bold text-[13px] text-[#062A43] flex items-center gap-1.5">
      <LineChart size={14} className="text-[#0C87BF]" />
      {spec.title}
    </h4>
    <MiniChart spec={spec} />
    <p className="font-ui text-[10.5px] text-[#8AA0B0] leading-[1.4]">
      {spec.source}
      {spec.thresholdSource ? ` · warning level: ${spec.thresholdSource}` : ''}
      {spec.baselineLabel ? ` · dashed line: ${spec.baselineLabel}` : ''}
    </p>
    {spec.notes?.map((note) => (
      <p key={note} className="font-ui text-[10.5px] text-[#5C6B76] leading-[1.4]">
        {note}
      </p>
    ))}
  </section>
);

const BriefBlock: React.FC<{ spec: BriefSpec }> = ({ spec }) => {
  const [open, setOpen] = useState(true);

  const asText = () =>
    [
      spec.title,
      `Compiled ${spec.compiledAt}`,
      `Position ${spec.position.latitude.toFixed(4)}, ${spec.position.longitude.toFixed(4)}`,
      '',
      ...spec.sections.flatMap((s) => [
        `## ${s.title}`,
        `Source: ${s.source}${s.issuedAt ? ` (issued ${s.issuedAt})` : ''}`,
        ...s.lines,
        '',
      ]),
      '## Caveats',
      ...spec.caveats,
    ].join('\n');

  return (
    <section className="w-full bg-white/95 border border-[#D8E6F0] rounded-2xl p-3 flex flex-col gap-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center justify-between gap-2 w-full text-left"
      >
        <span className="font-ui font-bold text-[13px] text-[#062A43] flex items-center gap-1.5">
          <FileText size={14} className="text-[#0B4A34]" />
          {spec.title}
        </span>
        {open ? <ChevronUp size={14} className="text-[#557186]" /> : <ChevronDown size={14} className="text-[#557186]" />}
      </button>

      <p className="font-ui text-[10.5px] text-[#8AA0B0]">
        Compiled {spec.compiledAt.replace('T', ' ')} · {spec.position.latitude.toFixed(3)},{' '}
        {spec.position.longitude.toFixed(3)}
      </p>

      {open && (
        <>
          {spec.sections.map((section) => (
            <div key={section.title} className="flex flex-col gap-0.5">
              <h5 className="font-ui font-bold text-[12px] text-[#062A43]">{section.title}</h5>
              {section.lines.map((line) => (
                <p key={line} className="font-ui text-[12px] text-[#274A62] leading-[1.45]">
                  {line}
                </p>
              ))}
              <p className="font-ui text-[10px] text-[#8AA0B0] leading-[1.35]">
                {section.source}
                {section.issuedAt ? ` · issued ${section.issuedAt}` : ''}
              </p>
            </div>
          ))}

          {spec.caveats.map((caveat) => (
            <p key={caveat} className="font-ui text-[11px] text-[#8A5A00] leading-[1.4]">
              {caveat}
            </p>
          ))}

          {/* Copy rather than download: a brief is usually pasted into a
              WhatsApp group or an email, not filed as a document. */}
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(asText())}
            className="self-start font-ui font-bold text-[11.5px] px-3 py-1.5 rounded-lg border border-[#0B4A34] text-[#0B4A34]"
          >
            Copy the brief
          </button>
        </>
      )}
    </section>
  );
};

const CatalogueBlock: React.FC<{ entries: CatalogueEntry[]; checkedLive: boolean }> = ({
  entries,
  checkedLive,
}) => {
  const [open, setOpen] = useState(false);
  const live = entries.filter((e) => !e.rejected);
  const rejected = entries.filter((e) => e.rejected);

  return (
    <section className="w-full bg-white/95 border border-[#D8E6F0] rounded-2xl p-3 flex flex-col gap-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center justify-between gap-2 w-full text-left"
      >
        <span className="font-ui font-bold text-[13px] text-[#062A43] flex items-center gap-1.5">
          <Database size={14} className="text-[#0C87BF]" />
          Where this comes from ({live.length} sources)
        </span>
        {open ? <ChevronUp size={14} className="text-[#557186]" /> : <ChevronDown size={14} className="text-[#557186]" />}
      </button>

      {open && (
        <>
          {live.map((entry) => (
            <div key={entry.key} className="flex flex-col gap-0.5 border-t border-[#EEF5FA] pt-1.5">
              <div className="flex items-center gap-1.5">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{
                    background:
                      entry.reachable === true
                        ? '#16A34A'
                        : entry.reachable === false
                          ? '#DC2626'
                          : '#94A3B8',
                  }}
                />
                <span className="font-ui font-semibold text-[12px] text-[#062A43]">
                  {entry.name}
                </span>
                {checkedLive && entry.latencyMs != null && (
                  <span className="font-ui text-[10px] text-[#8AA0B0]">{entry.latencyMs} ms</span>
                )}
              </div>
              <p className="font-ui text-[11px] text-[#557186] leading-[1.4] pl-3">
                {entry.provider} · {entry.resolution} · {entry.cadence}
              </p>
              {!entry.coversPosition && (
                <p className="font-ui text-[10.5px] text-[#B45309] pl-3">
                  Does not cover this position.
                </p>
              )}
            </div>
          ))}

          {rejected.length > 0 && (
            <div className="border-t border-[#EEF5FA] pt-2 flex flex-col gap-1.5">
              <h5 className="font-ui font-bold text-[11.5px] text-[#557186]">
                Investigated and not used
              </h5>
              {rejected.map((entry) => (
                <div key={entry.key}>
                  <p className="font-ui text-[11.5px] text-[#062A43] font-semibold">
                    {entry.name}
                  </p>
                  <p className="font-ui text-[11px] text-[#8A5A00] leading-[1.4]">
                    {entry.rejected}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
};

interface OrcaAgentArtifactsProps {
  results: AgentEvidence[];
}

export const OrcaAgentArtifacts: React.FC<OrcaAgentArtifactsProps> = ({ results }) => {
  const blocks: React.ReactNode[] = [];

  results.forEach((result, index) => {
    const data = (result.data ?? {}) as Record<string, unknown>;
    if (data.chart) {
      blocks.push(<ChartBlock key={`chart-${index}`} spec={data.chart as ChartSpec} />);
    }
    if (data.brief) {
      blocks.push(<BriefBlock key={`brief-${index}`} spec={data.brief as BriefSpec} />);
    }
    if (Array.isArray(data.catalogue)) {
      blocks.push(
        <CatalogueBlock
          key={`catalogue-${index}`}
          entries={data.catalogue as CatalogueEntry[]}
          checkedLive={Boolean(data.checkedLive)}
        />,
      );
    }
  });

  if (blocks.length === 0) return null;

  return <div className="w-full flex flex-col gap-2.5 mt-3">{blocks}</div>;
};

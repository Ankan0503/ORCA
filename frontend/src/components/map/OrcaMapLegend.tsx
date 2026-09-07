import React, { useState } from 'react';
import { Info, ChevronDown, ChevronUp } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';
import { MapLayerId } from './OrcaMapFilterBar';

/**
 * A key for what is actually on the map right now.
 *
 * The legend used to be fixed, listing best/good/avoid zones that no longer
 * exist, and it never changed with the layers. Switching to the rain and
 * current view produced coloured squares and teal arrows with nothing anywhere
 * explaining them — the user's own report was that they had no idea what the
 * lines meant.
 *
 * Each entry now belongs to a layer and appears only while that layer is on, so
 * the key and the picture cannot disagree.
 */
interface LegendEntry {
  layer: MapLayerId;
  label: string;
  /** A dot, a line or a filled square — matched to how it is drawn. */
  shape: 'dot' | 'line' | 'dashed' | 'square' | 'arrow';
  color: string;
}

const ENTRIES: LegendEntry[] = [
  { layer: 'fish', label: 'INCOIS fishing zone', shape: 'dot', color: '#EA580C' },
  { layer: 'fish', label: 'PFZ advisory line', shape: 'line', color: '#EA580C' },

  { layer: 'weather', label: 'Thunderstorm — lightning', shape: 'square', color: '#7C3AED' },
  { layer: 'weather', label: 'Heavy rain', shape: 'square', color: '#1D4ED8' },
  { layer: 'weather', label: 'Light rain', shape: 'square', color: '#60A5FA' },

  { layer: 'currents', label: 'Current (longer = faster)', shape: 'arrow', color: '#0E7490' },
  { layer: 'currents', label: 'Current not trusted here', shape: 'arrow', color: '#94A3B8' },

  { layer: 'limits', label: 'India EEZ', shape: 'line', color: '#0369A1' },
  { layer: 'limits', label: 'International border', shape: 'dashed', color: '#B91C1C' },
  { layer: 'limits', label: 'Protected area', shape: 'square', color: '#7C3AED' },
];

const Swatch: React.FC<{ entry: LegendEntry }> = ({ entry }) => {
  const { shape, color } = entry;
  if (shape === 'dot') {
    return (
      <span
        className="w-3 h-3 rounded-full shrink-0 border border-white shadow-2xs"
        style={{ backgroundColor: color }}
      />
    );
  }
  if (shape === 'square') {
    return (
      <span
        className="w-3 h-3 rounded-[3px] shrink-0 border border-white/70"
        style={{ backgroundColor: color, opacity: 0.65 }}
      />
    );
  }
  if (shape === 'arrow') {
    return (
      <span className="w-3.5 shrink-0 flex items-center" aria-hidden="true">
        <span className="h-0 w-2.5 border-t-2 rounded" style={{ borderColor: color }} />
        <span
          className="w-0 h-0 border-y-[3px] border-l-[5px] border-y-transparent"
          style={{ borderLeftColor: color }}
        />
      </span>
    );
  }
  // line / dashed
  return (
    <span
      className="w-3.5 h-0 shrink-0 rounded"
      style={{
        borderTopWidth: shape === 'dashed' ? 0 : 3,
        borderTopStyle: 'solid',
        borderTopColor: color,
        ...(shape === 'dashed'
          ? { borderTop: `3px dashed ${color}` }
          : {}),
      }}
    />
  );
};

interface OrcaMapLegendProps {
  translations: MapTranslations;
  activeLayers: MapLayerId[];
}

export const OrcaMapLegend: React.FC<OrcaMapLegendProps> = ({
  translations,
  activeLayers,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const visible = ENTRIES.filter((e) => activeLayers.includes(e.layer));

  return (
    <aside
      className="absolute top-[136px] sm:top-[144px] left-2.5 sm:left-4 z-20 pointer-events-auto select-none max-w-[190px] sm:max-w-[210px]"
      id="orca-map-legend"
      aria-label="Map key"
    >
      <div className="bg-white/95 backdrop-blur-md border border-[#D0DFEB] rounded-2xl shadow-md p-2 sm:p-2.5 flex flex-col gap-1.5 transition-all">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          id="orca-map-legend-toggle"
          aria-expanded={isExpanded}
          className="flex items-center justify-between gap-1 w-full text-left font-ui font-bold text-[11px] min-[390px]:text-[11.5px] uppercase tracking-wider text-[#557186] cursor-pointer hover:text-[#062A43] focus:outline-hidden"
        >
          <span className="flex items-center gap-1">
            <Info size={13} className="text-[#1677A8]" />
            <span>Key</span>
          </span>
          {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {isExpanded && (
          <ul className="flex flex-col gap-1 mt-0.5" role="list">
            {visible.map((entry) => (
              <li key={`${entry.layer}-${entry.label}`} className="flex items-center gap-2">
                <Swatch entry={entry} />
                <span className="font-ui font-semibold text-[11px] min-[390px]:text-[11.5px] text-[#062A43] leading-[1.2]">
                  {entry.label}
                </span>
              </li>
            ))}

            <li className="flex items-center gap-2 pt-1 mt-0.5 border-t border-[#E8F2F8]">
              <span className="w-3 h-3 rounded-full bg-[#2563EB] shrink-0 border-2 border-white shadow-2xs" />
              <span className="font-ui font-semibold text-[11px] min-[390px]:text-[11.5px] text-[#062A43] leading-[1.2]">
                {translations.youAreHere}
              </span>
            </li>

            {visible.length === 0 && (
              <li className="font-ui text-[11px] text-[#8AA0B0] leading-[1.3]">
                All layers are switched off — tap a chip above to bring one back.
              </li>
            )}
          </ul>
        )}
      </div>
    </aside>
  );
};

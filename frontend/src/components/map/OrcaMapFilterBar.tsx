import React from 'react';
import { MapTranslations } from '../../data/mapData';

/**
 * The map's layers, as things a fisherman would name rather than as categories.
 *
 * These used to be four mutually exclusive filters — "Fishing", "Safety", "PFZ",
 * "Restrictions" — with "Fishing" selected on load. Everything else was
 * therefore invisible until you guessed which tab it lived behind, and two of
 * the four showed the same fishing zones while a third showed nothing at all.
 * Rain over the sea sat behind a chip labelled "Safety", which is not a word
 * anyone would tap looking for weather.
 *
 * They are now independent toggles, all on by default: the map shows everything
 * it knows and lets you switch off what you do not want, instead of hiding its
 * work behind a name you have to guess.
 */
export type MapLayerId = 'fish' | 'weather' | 'currents' | 'limits' | 'copernicus-pfz';

export const ALL_LAYERS: MapLayerId[] = ['fish', 'weather', 'currents', 'limits', 'copernicus-pfz'];

interface LayerChip {
  id: MapLayerId;
  label: string;
  icon: string;
  /** Shown as the chip's title, so the colours have a plain-language meaning. */
  hint: string;
}

const CHIPS: LayerChip[] = [
  { id: 'fish', label: 'Fish zones', icon: '🎣', hint: "Today's INCOIS fishing zones" },
  { id: 'weather', label: 'Rain & storms', icon: '🌧️', hint: 'Rain and lightning over the sea' },
  { id: 'currents', label: 'Currents', icon: '🧭', hint: 'Which way the water is setting' },
  { id: 'limits', label: 'Borders & parks', icon: '🚫', hint: 'Sea borders and protected areas' },
  { id: 'copernicus-pfz', label: 'Copernicus PFZ', icon: '🛰️', hint: 'Satellite-derived cloud-bypass fishing zones (supplementary)' },
];

interface OrcaMapFilterBarProps {
  activeLayers: MapLayerId[];
  onToggleLayer: (layer: MapLayerId) => void;
  translations: MapTranslations;
}

export const OrcaMapFilterBar: React.FC<OrcaMapFilterBarProps> = ({
  activeLayers,
  onToggleLayer,
  translations,
}) => {
  return (
    <nav
      className="absolute top-[82px] sm:top-[88px] left-2.5 sm:left-4 right-2.5 sm:right-4 z-20 pointer-events-auto flex items-center justify-start gap-1.5 overflow-x-auto pb-1 no-scrollbar select-none"
      id="orca-map-filter-bar"
      aria-label={translations.ui.mapLayers}
    >
      <div className="flex items-center gap-1.5 bg-white/90 backdrop-blur-md p-1 rounded-full border border-[#D0DFEB] shadow-md">
        {CHIPS.map((chip) => {
          const isOn = activeLayers.includes(chip.id);
          return (
            <button
              key={chip.id}
              type="button"
              onClick={() => onToggleLayer(chip.id)}
              id={`map-layer-btn-${chip.id}`}
              aria-pressed={isOn}
              title={chip.hint}
              className={`min-h-[38px] px-3 sm:px-3.5 py-1.5 rounded-full font-ui text-[12.5px] min-[390px]:text-[13px] font-bold tracking-tight whitespace-nowrap flex items-center gap-1.5 transition-all duration-150 cursor-pointer active:scale-95 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40 ${
                isOn
                  ? 'bg-[#062A43] text-white shadow-sm'
                  : 'bg-transparent text-[#8AA0B0] hover:bg-[#EAF3FA] hover:text-[#274A62]'
              }`}
            >
              <span
                className={`text-[13px] leading-none ${isOn ? '' : 'opacity-45 grayscale'}`}
                aria-hidden="true"
              >
                {chip.icon}
              </span>
              <span>{chip.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

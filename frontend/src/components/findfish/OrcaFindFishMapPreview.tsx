import React from 'react';
import { Maximize2 } from 'lucide-react';
import { OrcaLeafletMap } from '../map/OrcaLeafletMap';
import { getMapTranslations } from '../../data/mapData';
import { LanguageOption } from '../../types';

interface OrcaFindFishMapPreviewProps {
  currentLanguage?: LanguageOption;
  /** Opens the full Map section. */
  onOpenFullMap: () => void;
}

/** Frames the harbour and the fishing zones together in a short card. */
const PREVIEW_CENTER: [number, number] = [21.54, 87.57];
const PREVIEW_ZOOM = 9;

/**
 * A real, correctly-positioned map of the fishing zones — but deliberately
 * static. Every gesture is disabled so it never traps a finger on this
 * scrolling page; tapping it opens the full Map section instead.
 */
export const OrcaFindFishMapPreview: React.FC<OrcaFindFishMapPreviewProps> = ({
  currentLanguage,
  onOpenFullMap,
}) => {
  const mapTranslations = getMapTranslations(currentLanguage?.code || 'en');

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpenFullMap();
    }
  };

  return (
    <section
      className="relative w-full rounded-2xl sm:rounded-3xl overflow-hidden border border-[#BCD4E4] bg-[#EAF4FB] shadow-md select-none"
      id="orca-find-fish-map-preview"
    >
      <div
        role="button"
        tabIndex={0}
        onClick={onOpenFullMap}
        onKeyDown={handleKeyDown}
        aria-label={mapTranslations.openFullMap}
        className="relative w-full h-[260px] min-[390px]:h-[300px] sm:h-[340px] cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5E9] focus-visible:ring-offset-2"
      >
        <OrcaLeafletMap
          activeFilter="fishing"
          showRoute
          onSelectZone={() => {}}
          translations={mapTranslations}
          interactive={false}
          attributionControl={false}
          center={PREVIEW_CENTER}
          zoom={PREVIEW_ZOOM}
        />

        {/* Tap affordance — the map itself gives no hint that it is a link. */}
        <div className="pointer-events-none absolute bottom-3 right-3 z-[500] flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 shadow-md">
          <Maximize2 size={14} className="text-[#0369A1]" />
          <span className="font-ui text-[12px] font-semibold text-[#06365A]">
            {mapTranslations.openFullMap}
          </span>
        </div>
      </div>

      {/* Legend footer, carried over from the previous map card. */}
      <div className="flex items-center gap-3 min-[390px]:gap-4 border-t border-[#BCD4E4] bg-white/80 px-3 min-[390px]:px-4 py-2.5">
        <LegendDot color="#10B981" label={mapTranslations.legend.best} />
        <LegendDot color="#F59E0B" label={mapTranslations.legend.good} />
        <LegendDot color="#EF4444" label={mapTranslations.legend.avoid} />
      </div>
    </section>
  );
};

const LegendDot: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <span className="flex items-center gap-1.5">
    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
    <span className="font-ui text-[11.5px] min-[390px]:text-[12.5px] font-medium text-[#274A62]">
      {label}
    </span>
  </span>
);

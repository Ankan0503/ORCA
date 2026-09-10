import React from 'react';
import { Plus, Minus, Navigation } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';

interface OrcaMapControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetLocation: () => void;
  translations: MapTranslations;
}

export const OrcaMapControls: React.FC<OrcaMapControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onResetLocation,
  translations,
}) => {
  return (
    <aside
      className="absolute top-[136px] sm:top-[144px] right-2.5 sm:right-4 z-20 pointer-events-auto flex flex-col items-center gap-2 select-none"
      id="orca-map-controls"
      aria-label={translations.ui.mapNavigationControls}
    >
      {/* Zoom In & Out Cluster */}
      <div className="flex flex-col bg-white/95 backdrop-blur-md rounded-2xl border border-[#D0DFEB] shadow-md overflow-hidden">
        <button
          type="button"
          onClick={onZoomIn}
          id="orca-map-zoom-in-btn"
          aria-label={translations.ui.zoomIn}
          className="w-[44px] h-[44px] min-[390px]:w-[48px] min-[390px]:h-[48px] flex items-center justify-center text-[#062A43] hover:bg-[#F0F7FB] active:bg-[#E2F0F9] transition-colors cursor-pointer border-b border-[#E2EDF5] focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40"
        >
          <Plus size={22} className="stroke-[2.6]" />
        </button>

        <button
          type="button"
          onClick={onZoomOut}
          id="orca-map-zoom-out-btn"
          aria-label={translations.ui.zoomOut}
          className="w-[44px] h-[44px] min-[390px]:w-[48px] min-[390px]:h-[48px] flex items-center justify-center text-[#062A43] hover:bg-[#F0F7FB] active:bg-[#E2F0F9] transition-colors cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40"
        >
          <Minus size={22} className="stroke-[2.6]" />
        </button>
      </div>

      {/* Re-center / My Location Button */}
      <button
        type="button"
        onClick={onResetLocation}
        id="orca-map-my-location-btn"
        aria-label={translations.ui.centreOnMyLocation}
        title={translations.myLocation}
        className="w-[44px] h-[44px] min-[390px]:w-[48px] min-[390px]:h-[48px] rounded-2xl bg-white/95 backdrop-blur-md border border-[#D0DFEB] shadow-md flex flex-col items-center justify-center text-[#1677A8] hover:text-[#062A43] hover:bg-[#F0F7FB] active:scale-95 transition-all cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40"
      >
        <Navigation size={20} className="fill-[#1677A8] text-[#1677A8] -rotate-45" />
        <span className="font-ui text-[9px] font-extrabold tracking-tighter text-[#062A43] leading-none mt-0.5">
          GPS
        </span>
      </button>
    </aside>
  );
};

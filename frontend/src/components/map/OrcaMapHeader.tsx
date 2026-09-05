import React from 'react';
import { ArrowLeft, MapPin, Wifi, WifiOff } from 'lucide-react';
import { LanguageOption } from '../../types';
import { getMapTranslations } from '../../data/mapData';

const ORCA_LOGO = '/assets/orca-logo.svg';

interface OrcaMapHeaderProps {
  onBackClick: () => void;
  currentLanguage?: LanguageOption;
  isOffline?: boolean;
  onToggleOffline?: () => void;
  locationName?: string;
  onLocationClick?: () => void;
}

export const OrcaMapHeader: React.FC<OrcaMapHeaderProps> = ({
  onBackClick,
  currentLanguage,
  isOffline = false,
  onToggleOffline,
  locationName = 'Digha, West Bengal',
  onLocationClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const t = getMapTranslations(langCode);

  return (
    <header
      className="absolute top-2.5 sm:top-3.5 left-2.5 sm:left-4 right-2.5 sm:right-4 z-30 pointer-events-auto flex flex-col gap-1.5 select-none"
      id="orca-map-top-header"
      aria-label="Map header"
    >
      {/* Top Bar: Back button, Logo, and Location Badge */}
      <div className="w-full flex items-center justify-between gap-2.5">
        {/* Left: Back Arrow + Logo */}
        <div className="flex items-center gap-2 min-[390px]:gap-2.5 shrink-0">
          <button
            type="button"
            onClick={onBackClick}
            id="orca-map-back-btn"
            aria-label="Go back to Home"
            className="w-[42px] h-[42px] min-[390px]:w-[44px] min-[390px]:h-[44px] rounded-full bg-white/95 backdrop-blur-md border border-[#D0DFEB] text-[#062A43] shadow-md flex items-center justify-center hover:bg-white active:scale-95 transition-all duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/30 shrink-0"
          >
            <ArrowLeft size={21} className="text-[#062A43] stroke-[2.4]" />
          </button>

          {/* ORCA Logo in white pill badge for contrast over map */}
          <div className="px-2.5 py-1.5 rounded-full bg-white/95 backdrop-blur-md border border-[#D0DFEB] shadow-md flex items-center shrink-0">
            <img
              src={ORCA_LOGO}
              alt="ORCA"
              className="w-[84px] min-[390px]:w-[92px] h-auto object-contain block"
            />
          </div>
        </div>

        {/* Right: Location & Offline/Status Toggle */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Location Badge */}
          <button
            type="button"
            onClick={onLocationClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 min-[390px]:px-3.5 min-[390px]:py-2 rounded-full bg-white/95 backdrop-blur-md border border-[#D0DFEB] shadow-md max-w-[170px] min-[390px]:max-w-[210px] cursor-pointer hover:border-[#1677A8] active:scale-98 transition-all focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#1677A8]"
            aria-label={`Change location. Currently ${locationName || t.locationName}`}
          >
            <MapPin size={14} className="text-[#1677A8] shrink-0 stroke-[2.4]" />
            <span className="font-ui text-[12px] min-[390px]:text-[13px] font-bold text-[#062A43] truncate">
              {locationName || t.locationName}
            </span>
          </button>

          {/* Offline indicator / Low internet badge */}
          <button
            type="button"
            onClick={onToggleOffline}
            id="orca-map-offline-toggle"
            title={isOffline ? 'Offline mode enabled' : 'Online • Tap to simulate offline'}
            aria-label={isOffline ? 'Offline mode' : 'Online updated'}
            className={`w-[36px] h-[36px] min-[390px]:w-[38px] min-[390px]:h-[38px] rounded-full border shadow-md flex items-center justify-center transition-all cursor-pointer ${
              isOffline
                ? 'bg-[#FEF2F2] border-[#FCA5A5] text-[#DC2626]'
                : 'bg-white/95 border-[#D0DFEB] text-[#16A34A] hover:bg-[#F0FDF4]'
            }`}
          >
            {isOffline ? (
              <WifiOff size={16} className="stroke-[2.2]" />
            ) : (
              <Wifi size={16} className="stroke-[2.2]" />
            )}
          </button>
        </div>
      </div>

      {/* Sub-bar: Status note (● Updated 12 mins ago / ◐ Offline) */}
      <div className="flex items-center justify-between px-1">
        <div
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] min-[390px]:text-[11.5px] font-ui font-semibold shadow-xs backdrop-blur-md border ${
            isOffline
              ? 'bg-[#FEF2F2]/95 border-[#FCA5A5] text-[#991B1B]'
              : 'bg-white/90 border-[#D8E6F0] text-[#426078]'
          }`}
          role="status"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isOffline ? 'bg-[#DC2626]' : 'bg-[#16A34A] animate-pulse'
            }`}
            aria-hidden="true"
          />
          <span>{isOffline ? t.offlineMode : t.updatedMinsAgo}</span>
        </div>
      </div>
    </header>
  );
};

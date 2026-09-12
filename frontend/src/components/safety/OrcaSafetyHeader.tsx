import React from 'react';
import { ArrowLeft, MapPin } from 'lucide-react';
import { LanguageOption } from '../../types';
import { getHomeTranslation } from '../../data/homeTranslations';
import { OrcaSosButton } from '../safety/OrcaSosButton';

const ORCA_LOGO = '/assets/orca-logo.svg';

interface OrcaSafetyHeaderProps {
  onBackClick: () => void;
  currentLanguage?: LanguageOption;
  locationName?: string;
  /** Opens the location picker; the chip is the control for changing location. */
  onLocationClick?: () => void;
}

export const OrcaSafetyHeader: React.FC<OrcaSafetyHeaderProps> = ({
  onBackClick,
  currentLanguage,
  locationName,
  onLocationClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const homeTranslation = getHomeTranslation(langCode);
  const displayLocation = locationName || homeTranslation.locationName;

  return (
    <header
      className="relative z-20 w-full flex items-center justify-between gap-2.5 pt-2 min-[390px]:pt-3 sm:pt-4 pb-1 sm:pb-2"
      id="orca-safety-header"
      aria-label="Safety navigation header"
    >
      {/* Left: Back button + ORCA Logo */}
      <div className="flex items-center gap-2 min-[390px]:gap-2.5 sm:gap-3.5 shrink-0">
        <button
          type="button"
          onClick={onBackClick}
          id="orca-safety-back-btn"
          aria-label="Go back to Home"
          className="w-[38px] h-[38px] min-[390px]:w-[42px] min-[390px]:h-[42px] rounded-full bg-white/90 backdrop-blur-md border border-[#D8E6F0] text-[#062A43] shadow-xs flex items-center justify-center hover:bg-white active:scale-95 transition-all duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/30 shrink-0"
        >
          <ArrowLeft size={18} className="text-[#062A43] stroke-[2.4]" />
        </button>

        {/* ORCA Logo */}
        <div className="shrink-0 flex items-center">
          <img
            src={ORCA_LOGO}
            alt="ORCA"
            className="w-[90px] min-[390px]:w-[100px] sm:w-[110px] h-auto object-contain block"
          />
        </div>
      </div>

      {/* Right: distress, then location. SOS rides in every header so it is
          one tap from wherever the fisherman is. */}
      <div className="flex items-center gap-2 shrink-0 max-w-[70%]">
        <OrcaSosButton variant="chip" languageCode={currentLanguage?.code || 'en'} />
      <button
        type="button"
        onClick={onLocationClick}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 min-[390px]:px-3 min-[390px]:py-1.5 sm:px-3.5 sm:py-2 rounded-full bg-white/85 backdrop-blur-md border border-[#D8E6F0]/80 shadow-xs max-w-[50%] min-[390px]:max-w-[56%] cursor-pointer hover:bg-white active:scale-98 transition-all focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#1677A8]"
        aria-label={`Change location. Currently ${displayLocation}`}
      >
        <MapPin size={13} className="text-[#1677A8] shrink-0 stroke-[2.2]" />
        <span className="font-ui text-[11.5px] min-[390px]:text-[12.5px] sm:text-[13px] font-semibold tracking-tight text-[#062A43] truncate">
          {displayLocation}
        </span>
      </button>
      </div>
    </header>
  );
};

import React from 'react';
import { X, Compass, Clock, ShieldCheck, MapPin, Navigation } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaNavigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  translations: FindFishTranslations;
}

export const OrcaNavigationModal: React.FC<OrcaNavigationModalProps> = ({
  isOpen,
  onClose,
  translations,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/45 backdrop-blur-xs transition-opacity select-none"
      role="dialog"
      aria-modal="true"
      aria-labelledby="nav-modal-title"
    >
      <div
        className="w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-6 sm:p-7 shadow-2xl border border-[#D5E5F0] flex flex-col gap-4 animate-in fade-in slide-in-from-bottom duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-[#EBF7EE] text-[#15803D] flex items-center justify-center font-bold">
              🎣
            </div>
            <div>
              <span className="font-ui font-extrabold text-[11px] text-[#15803D] tracking-wider uppercase">
                {translations.bestAreaBadge}
              </span>
              <h3 id="nav-modal-title" className="font-display font-bold text-[22px] text-[#062A43] leading-none">
                {translations.bestDistance}
              </h3>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation details"
            className="w-9 h-9 rounded-full bg-[#F0F5F9] hover:bg-[#E2EDF4] flex items-center justify-center text-[#5A7385] cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Essential Navigation Specs: large and visual */}
        <div className="grid grid-cols-2 gap-2.5 pt-2">
          {/* Compass Heading */}
          <div className="p-3.5 rounded-xl bg-[#F0F7FD] border border-[#D0E5F5] flex flex-col">
            <div className="flex items-center gap-1.5 text-[#1677A8] text-[12px] font-semibold">
              <Compass size={14} className="stroke-[2.5]" />
              <span>Heading</span>
            </div>
            <span className="font-ui font-bold text-[16px] text-[#062A43] mt-1">
              {translations.compassHeading}
            </span>
          </div>

          {/* Travel Time */}
          <div className="p-3.5 rounded-xl bg-[#F0F7FD] border border-[#D0E5F5] flex flex-col">
            <div className="flex items-center gap-1.5 text-[#1677A8] text-[12px] font-semibold">
              <Clock size={14} className="stroke-[2.5]" />
              <span>Travel Time</span>
            </div>
            <span className="font-ui font-bold text-[16px] text-[#062A43] mt-1">
              {translations.travelTime}
            </span>
          </div>

          {/* Sea Condition */}
          <div className="col-span-2 p-3.5 rounded-xl bg-[#EBF7EE] border border-[#BDE5CA] flex items-center gap-3">
            <ShieldCheck size={22} className="text-[#15803D] shrink-0 stroke-[2.4]" />
            <div className="flex flex-col">
              <span className="font-ui font-bold text-[14px] text-[#166534]">
                {translations.seaCondition}
              </span>
              <span className="font-ui text-[12px] text-[#2D5A40]">
                Waves 0.8m • Winds 12 km/h • Good visibility
              </span>
            </div>
          </div>
        </div>

        {/* Departure Point */}
        <div className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-[#FAFBFD] border border-[#E5EEF5] text-[13px] text-[#334D5E]">
          <span className="flex items-center gap-1.5 font-medium">
            <MapPin size={14} className="text-[#1677A8]" />
            Depart from:
          </span>
          <span className="font-bold text-[#062A43]">
            {translations.mapCurrentLocation}
          </span>
        </div>

        {/* Big Acknowledge Button */}
        <button
          type="button"
          onClick={onClose}
          className="w-full h-12 rounded-xl bg-[#0B4A34] text-white font-ui font-bold text-[16px] hover:bg-[#073625] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md mt-1"
        >
          <Navigation size={18} className="rotate-45 stroke-[2.5]" />
          <span>{translations.modalClose}</span>
        </button>
      </div>
    </div>
  );
};

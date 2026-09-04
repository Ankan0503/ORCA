import React from 'react';
import { ArrowRight, CheckCircle2, Navigation, Compass } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';

interface OrcaMapCardProps {
  onCardClick: () => void;
  onNavigateToFindFish: () => void;
  onToggleRoute?: () => void;
  showRoute?: boolean;
  translations: MapTranslations;
}

export const OrcaMapCard: React.FC<OrcaMapCardProps> = ({
  onCardClick,
  onNavigateToFindFish,
  onToggleRoute,
  showRoute = true,
  translations,
}) => {
  return (
    <section
      className="absolute bottom-[80px] min-[390px]:bottom-[86px] sm:bottom-[92px] left-3 sm:left-4 right-3 sm:right-4 z-30 pointer-events-auto max-w-[620px] mx-auto select-none"
      id="orca-map-floating-recommendation"
      aria-label="Best fishing area recommendation"
    >
      <div
        role="button"
        tabIndex={0}
        onClick={onCardClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onCardClick();
          }
        }}
        className="w-full bg-white/95 backdrop-blur-md border-2 border-[#16A34A] rounded-2xl sm:rounded-3xl p-3.5 min-[390px]:p-4 shadow-[0_8px_30px_rgba(6,42,67,0.14)] hover:border-[#15803D] active:scale-[0.99] transition-all cursor-pointer flex flex-col gap-2.5 focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#16A34A]/40"
      >
        {/* Top Header: Badge + Distance */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[20px] min-[390px]:text-[22px] leading-none shrink-0" aria-hidden="true">
              🎣
            </span>
            <div className="flex flex-col">
              <span className="font-ui font-extrabold text-[15px] min-[390px]:text-[16px] sm:text-[17px] text-[#062A43] leading-tight">
                {translations.bestCard.title}
              </span>
              <span className="font-ui text-[12px] min-[390px]:text-[13px] font-bold text-[#15803D]">
                {translations.bestCard.distance}
              </span>
            </div>
          </div>

          {/* Direct action arrow button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onNavigateToFindFish();
            }}
            id="orca-map-card-go-btn"
            aria-label="Navigate to Find Fish details"
            className="w-[42px] h-[42px] rounded-full bg-[#062A43] hover:bg-[#06365A] active:scale-95 text-white flex items-center justify-center transition-all cursor-pointer shadow-sm shrink-0"
          >
            <ArrowRight size={20} className="stroke-[2.5]" />
          </button>
        </div>

        {/* Sub-status: Good fishing chance • Safe to go */}
        <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#E8F2F8]">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <div className="inline-flex items-center gap-1.5 font-ui text-[12px] min-[390px]:text-[12.5px] font-semibold text-[#166534]">
              <CheckCircle2 size={15} className="text-[#16A34A] stroke-[2.4]" />
              <span>{translations.bestCard.chance}</span>
            </div>

            <div className="inline-flex items-center gap-1.5 font-ui text-[12px] min-[390px]:text-[12.5px] font-semibold text-[#166534]">
              <span className="w-2 h-2 rounded-full bg-[#16A34A]" />
              <span>{translations.bestCard.safety}</span>
            </div>
          </div>

          {/* Route toggle pill */}
          {onToggleRoute && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleRoute();
              }}
              id="orca-map-route-toggle"
              aria-label={showRoute ? 'Hide route line' : 'Show route line'}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] min-[390px]:text-[11.5px] font-ui font-bold transition-colors cursor-pointer shrink-0 ${
                showRoute
                  ? 'bg-[#E5F7EB] text-[#15803D] border border-[#BBEACE]'
                  : 'bg-[#F0F6FA] text-[#557186] border border-[#D0DFEB]'
              }`}
            >
              <Compass size={13} className="stroke-[2.4]" />
              <span>{showRoute ? 'Route ON' : 'Show route'}</span>
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

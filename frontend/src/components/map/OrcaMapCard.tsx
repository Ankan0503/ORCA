import React from 'react';
import { ArrowRight, CheckCircle2, Compass } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';
import { PfzAdvisory } from '../../services/orcaApi';

interface OrcaMapCardProps {
  onCardClick: () => void;
  onNavigateToFindFish: () => void;
  translations: MapTranslations;
  /** The real INCOIS advisory for the user's coast; null while loading or unavailable. */
  advisory: PfzAdvisory | null;
}

/**
 * The floating map card. Every value shown is the nearest INCOIS advisory zone
 * for the user's sector — the old hardcoded "12 km offshore / Safe to go" text
 * was removed along with the invented zones it described.
 */
export const OrcaMapCard: React.FC<OrcaMapCardProps> = ({
  onCardClick,
  onNavigateToFindFish,
  translations,
  advisory,
}) => {
  const nearest = advisory?.points?.[0] ?? null;

  const headline = nearest
    ? nearest.distance_km_from != null && nearest.distance_km_to != null
      ? `${nearest.distance_km_from}–${nearest.distance_km_to} km offshore`
      : `${nearest.range_km ?? ''} km away`
    : advisory?.empty
      ? 'No advisory issued today'
      : 'Loading advisory…';

  const subline = nearest
    ? `Off ${nearest.landing_centre}`
    : advisory?.empty
      ? `INCOIS issued none for ${advisory.sector_name}`
      : '';

  return (
    <section
      className="absolute bottom-[80px] min-[390px]:bottom-[86px] sm:bottom-[92px] left-3 sm:left-4 right-3 sm:right-4 z-30 pointer-events-auto max-w-[620px] mx-auto select-none"
      id="orca-map-floating-recommendation"
      aria-label={translations.ui.bestFishingAreaRecommendation}
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
            <div className="flex flex-col min-w-0">
              <span className="font-ui font-extrabold text-[15px] min-[390px]:text-[16px] sm:text-[17px] text-[#062A43] leading-tight truncate">
                {headline}
              </span>
              <span className="font-ui text-[12px] min-[390px]:text-[13px] font-bold text-[#15803D] truncate">
                {subline}
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
            aria-label={translations.ui.navigateToFindFish}
            className="w-[42px] h-[42px] rounded-full bg-[#062A43] hover:bg-[#06365A] active:scale-95 text-white flex items-center justify-center transition-all cursor-pointer shadow-sm shrink-0"
          >
            <ArrowRight size={20} className="stroke-[2.5]" />
          </button>
        </div>

        {/* Sub-status: the real advisory's bearing, depth and source date */}
        <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#E8F2F8]">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
            {nearest && (
              <div className="inline-flex items-center gap-1.5 font-ui text-[12px] min-[390px]:text-[12.5px] font-semibold text-[#166534]">
                <Compass size={14} className="text-[#16A34A] stroke-[2.4]" />
                <span>
                  {nearest.bearing_deg != null
                    ? `${nearest.direction} (${nearest.bearing_deg}°)`
                    : nearest.direction}
                  {nearest.depth_m_from != null && nearest.depth_m_to != null
                    ? ` · ${nearest.depth_m_from}–${nearest.depth_m_to} m`
                    : ''}
                </span>
              </div>
            )}

            {/*
              Tapping the card plans the passage, which nothing previously
              said. The route was built and then left undiscoverable behind an
              unlabelled tap target.
            */}
            <div className="inline-flex items-center gap-1.5 font-ui text-[12px] font-bold text-[#0B4A34] bg-[#E5F7EB] border border-[#BBEACE] rounded-full px-2.5 py-1">
              <Compass size={13} className="stroke-[2.6]" />
              <span>{translations.ui.tapToPlanRoute}</span>
            </div>

            {advisory?.forecast_date && (
              <div className="inline-flex items-center gap-1.5 font-ui text-[12px] min-[390px]:text-[12.5px] font-semibold text-[#0C587F] min-w-0">
                <CheckCircle2 size={14} className="text-[#1677A8] stroke-[2.4] shrink-0" />
                <span className="truncate">
                  INCOIS · {advisory.forecast_date}
                  {advisory.stale ? ' (last available)' : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

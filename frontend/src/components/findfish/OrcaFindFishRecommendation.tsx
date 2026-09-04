import React from 'react';
import { ArrowRight, Compass, ShieldCheck } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaFindFishRecommendationProps {
  translations: FindFishTranslations;
  onGoHere: () => void;
}

export const OrcaFindFishRecommendation: React.FC<OrcaFindFishRecommendationProps> = ({
  translations,
  onGoHere,
}) => {
  return (
    <div
      className="relative w-full rounded-2xl sm:rounded-3xl p-5 min-[390px]:p-6 sm:p-7 bg-[#EBF7EE] border-2 border-[#A6DDB6] shadow-md transition-all select-none"
      id="orca-main-recommendation-card"
      aria-label="ORCA Primary Fishing Recommendation"
    >
      {/* Top row: Icon + BEST AREA badge */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Visual Hook / Fish icon */}
          <div className="w-11 h-11 min-[390px]:w-12 min-[390px]:h-12 rounded-2xl bg-white border border-[#A6DDB6] flex items-center justify-center text-2xl shadow-xs shrink-0">
            <span role="img" aria-label="Fishing hook and fish">🎣</span>
          </div>

          {/* BEST AREA Pill */}
          <span className="inline-flex items-center px-3 py-1 rounded-full bg-[#15803D] text-white font-ui font-extrabold text-[12px] min-[390px]:text-[13px] tracking-wider uppercase shadow-xs">
            {translations.bestAreaBadge}
          </span>
        </div>

        {/* Sea Safety confirmation pill */}
        <div className="hidden min-[400px]:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/80 border border-[#A6DDB6] text-[#166534] text-[12px] font-semibold">
          <ShieldCheck size={14} className="stroke-[2.5]" />
          <span>Safe sea</span>
        </div>
      </div>

      {/* Prominent Distance & Title */}
      <div className="mt-4 sm:mt-5 flex flex-col items-start">
        {/* 12 km offshore: Visually dominant */}
        <h2 className="font-display font-bold text-[32px] min-[390px]:text-[36px] sm:text-[42px] text-[#062A43] leading-[1.05] tracking-tight">
          {translations.bestDistance}
        </h2>

        {/* Good fishing chance: High confidence subhead */}
        <div className="font-ui font-bold text-[18px] min-[390px]:text-[20px] sm:text-[22px] text-[#15803D] mt-1.5 flex items-center gap-2">
          <span>{translations.bestChance}</span>
        </div>

        {/* Good fish conditions + safe sea: Plain spoken explanation */}
        <p className="font-ui font-medium text-[15px] min-[390px]:text-[16px] sm:text-[17px] text-[#244A37] mt-1.5 leading-[1.35]">
          {translations.bestReason}
        </p>
      </div>

      {/* 
        PROMINENT ACTION BUTTON:
        "GO HERE →"
        Touch target >= 48px, bold, high contrast, inviting tap
      */}
      <div className="mt-5 sm:mt-6 pt-4 border-t border-[#A6DDB6]/60 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={onGoHere}
          id="orca-go-here-btn"
          aria-label={`Go to ${translations.bestDistance} - ${translations.bestChance}`}
          className="w-full h-12 min-[390px]:h-13 sm:h-14 px-6 rounded-xl sm:rounded-2xl bg-[#0B4A34] text-white hover:bg-[#073625] active:scale-[0.98] shadow-md hover:shadow-lg transition-all duration-150 flex items-center justify-center gap-3 cursor-pointer focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#0B4A34]/40"
        >
          <span className="font-ui font-bold text-[16px] min-[390px]:text-[17.5px] tracking-wide uppercase">
            {translations.goHereBtn}
          </span>
          <ArrowRight size={20} className="stroke-[2.8]" />
        </button>
      </div>
    </div>
  );
};

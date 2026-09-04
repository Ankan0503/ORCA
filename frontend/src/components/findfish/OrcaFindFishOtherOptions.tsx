import React from 'react';
import { ArrowRight } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaFindFishOtherOptionsProps {
  translations: FindFishTranslations;
  onSelectOption?: (distance: string) => void;
}

export const OrcaFindFishOtherOptions: React.FC<OrcaFindFishOtherOptionsProps> = ({
  translations,
  onSelectOption,
}) => {
  return (
    <section
      className="w-full flex flex-col gap-2.5 sm:gap-3 select-none"
      id="orca-other-fishing-options"
      aria-label="Alternative fishing areas"
    >
      {/* Section Subhead: clearly secondary */}
      <h3 className="font-ui font-semibold text-[14px] min-[390px]:text-[15px] text-[#4A677B] tracking-tight uppercase px-1">
        {translations.otherOptionsTitle}
      </h3>

      {/* Grid of two small horizontal cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
        {/* Option 1: 18 km offshore */}
        <button
          type="button"
          onClick={() => onSelectOption?.('18 km')}
          aria-label={`${translations.otherOption1Distance} - ${translations.otherOption1Chance}`}
          className="w-full text-left p-3.5 min-[390px]:p-4 rounded-xl bg-white/90 backdrop-blur-sm border border-[#D5E4EE] hover:border-[#BED6E6] hover:bg-white active:scale-[0.99] shadow-2xs transition-all duration-150 flex items-center justify-between gap-3 cursor-pointer group focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#1677A8]/30"
        >
          <div className="flex flex-col items-start min-w-0">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#EAB308] shrink-0" />
              <span className="font-display font-bold text-[18px] min-[390px]:text-[19px] text-[#062A43] leading-none">
                {translations.otherOption1Distance}
              </span>
            </div>
            <span className="font-ui text-[13px] text-[#557186] font-medium mt-1">
              {translations.otherOption1Chance}
            </span>
            <span className="font-ui text-[12px] font-semibold text-[#1677A8] group-hover:text-[#0C587F] transition-colors mt-0.5">
              {translations.otherOption1Action}
            </span>
          </div>

          <div className="w-8 h-8 rounded-full bg-[#F0F6FA] group-hover:bg-[#E3EFF7] flex items-center justify-center text-[#1677A8] shrink-0 transition-colors">
            <ArrowRight size={16} />
          </div>
        </button>

        {/* Option 2: 25 km offshore */}
        <button
          type="button"
          onClick={() => onSelectOption?.('25 km')}
          aria-label={`${translations.otherOption2Distance} - ${translations.otherOption2Chance}`}
          className="w-full text-left p-3.5 min-[390px]:p-4 rounded-xl bg-white/90 backdrop-blur-sm border border-[#D5E4EE] hover:border-[#BED6E6] hover:bg-white active:scale-[0.99] shadow-2xs transition-all duration-150 flex items-center justify-between gap-3 cursor-pointer group focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#1677A8]/30"
        >
          <div className="flex flex-col items-start min-w-0">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#EAB308] shrink-0" />
              <span className="font-display font-bold text-[18px] min-[390px]:text-[19px] text-[#062A43] leading-none">
                {translations.otherOption2Distance}
              </span>
            </div>
            <span className="font-ui text-[13px] text-[#557186] font-medium mt-1">
              {translations.otherOption2Chance}
            </span>
            <span className="font-ui text-[12px] font-semibold text-[#1677A8] group-hover:text-[#0C587F] transition-colors mt-0.5">
              {translations.otherOption2Action}
            </span>
          </div>

          <div className="w-8 h-8 rounded-full bg-[#F0F6FA] group-hover:bg-[#E3EFF7] flex items-center justify-center text-[#1677A8] shrink-0 transition-colors">
            <ArrowRight size={16} />
          </div>
        </button>
      </div>
    </section>
  );
};

import React from 'react';
import { Lightbulb } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaFindFishQuickTipProps {
  translations: FindFishTranslations;
}

export const OrcaFindFishQuickTip: React.FC<OrcaFindFishQuickTipProps> = ({
  translations,
}) => {
  return (
    <div
      className="w-full p-3.5 min-[390px]:p-4 rounded-xl sm:rounded-2xl bg-[#FFFBEB] border border-[#FDE68A] shadow-2xs flex items-start gap-3 select-none"
      role="note"
      aria-label="Quick fishing tip"
    >
      <div className="w-8 h-8 rounded-full bg-[#FEF3C7] text-[#D97706] flex items-center justify-center shrink-0 mt-0.5">
        <Lightbulb size={17} className="stroke-[2.5]" />
      </div>

      <div className="flex flex-col min-w-0">
        <span className="font-ui font-bold text-[13.5px] min-[390px]:text-[14px] text-[#92400E] leading-tight">
          {translations.quickTipTitle}
        </span>
        <p className="font-ui text-[13.5px] min-[390px]:text-[14px] text-[#78350F] leading-[1.4] mt-0.5">
          {translations.quickTipText}
        </p>
      </div>
    </div>
  );
};

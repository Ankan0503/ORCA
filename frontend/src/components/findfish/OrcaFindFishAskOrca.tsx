import React, { useState } from 'react';
import { Mic, Sparkles, MessageCircleQuestion } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaFindFishAskOrcaProps {
  translations: FindFishTranslations;
}

export const OrcaFindFishAskOrca: React.FC<OrcaFindFishAskOrcaProps> = ({
  translations,
}) => {
  const [isAnswering, setIsAnswering] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const handleAskQuestion = () => {
    setIsAnswering(true);
    setTimeout(() => {
      setIsAnswering(false);
      setAnswer(
        'Calm 0.8m waves and a stable chlorophyll gradient 12 km off Digha indicate active baitfish schools with low tidal turbulence today.'
      );
    }, 600);
  };

  return (
    <div
      className="w-full p-4 min-[390px]:p-5 rounded-2xl bg-white/90 backdrop-blur-sm border border-[#D5E5F0] shadow-xs select-none"
      id="orca-findfish-ask-card"
    >
      <div className="flex items-center justify-between gap-3">
        {/* Left info */}
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-1.5">
            <Sparkles size={15} className="text-[#1677A8]" />
            <h4 className="font-ui font-bold text-[15px] min-[390px]:text-[16px] text-[#062A43]">
              {translations.askOrcaTitle}
            </h4>
          </div>
          <p className="font-ui text-[13px] min-[390px]:text-[13.5px] text-[#4A677B] mt-0.5">
            {translations.askOrcaPrompt}
          </p>
        </div>

        {/* Microphone Voice Button */}
        <button
          type="button"
          onClick={handleAskQuestion}
          aria-label="Voice question to ORCA"
          className="w-11 h-11 min-[390px]:w-12 min-[390px]:h-12 rounded-full bg-[#EBF4FA] border border-[#BEDCF0] text-[#1677A8] hover:bg-[#DCEEF8] active:scale-95 transition-all flex items-center justify-center cursor-pointer shrink-0 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#1677A8]/40"
        >
          <Mic size={20} className="stroke-[2.4]" />
        </button>
      </div>

      {/* Suggested Question Chip */}
      <div className="mt-3 pt-3 border-t border-[#EDF4F9] flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleAskQuestion}
          disabled={isAnswering}
          aria-label={`Ask ORCA: ${translations.askOrcaChip}`}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#F4F9FD] hover:bg-[#E7F3FB] border border-[#CFE4F3] text-[#062A43] font-ui text-[12.5px] min-[390px]:text-[13px] font-semibold transition-colors cursor-pointer active:scale-98 disabled:opacity-60"
        >
          <MessageCircleQuestion size={14} className="text-[#1677A8]" />
          <span>“{translations.askOrcaChip}”</span>
        </button>

        {isAnswering && (
          <span className="font-ui text-[12px] text-[#1677A8] italic animate-pulse">
            Consulting marine intelligence...
          </span>
        )}
      </div>

      {/* Answer feedback */}
      {answer && (
        <div className="mt-2.5 p-3 rounded-xl bg-[#F0F8FF] border border-[#BCE1F9] text-[13px] text-[#0C4A6E] font-ui leading-relaxed">
          {answer}
        </div>
      )}
    </div>
  );
};

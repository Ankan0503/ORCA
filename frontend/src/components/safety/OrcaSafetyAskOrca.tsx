import React from 'react';
import { Mic } from 'lucide-react';

interface OrcaSafetyAskOrcaProps {
  title?: string;
  subtext?: string;
  prompt1?: string;
  prompt2?: string;
  onVoiceClick?: () => void;
  onPromptClick?: (prompt: string) => void;
}

export const OrcaSafetyAskOrca: React.FC<OrcaSafetyAskOrcaProps> = ({
  title = 'Ask ORCA',
  subtext = 'Want to know why?',
  prompt1 = '“Can I go farther offshore?”',
  prompt2 = '“When will the waves get higher?”',
  onVoiceClick,
  onPromptClick,
}) => {
  return (
    <section
      className="w-full mt-6 mb-8 select-none"
      id="orca-safety-ask-section"
      aria-label="Ask ORCA follow-up voice query"
    >
      <div className="w-full rounded-[20px] bg-[#E5F1F9] border border-[#BCD8EC] p-4 min-[390px]:p-4.5 sm:p-5 shadow-[0_3px_14px_rgba(6,42,67,0.05)] flex flex-col gap-3">
        {/* Top row: Title + Subtext + Microphone button */}
        <div className="w-full flex items-center justify-between gap-3">
          <div className="flex flex-col">
            <h3 className="font-ui font-bold text-[16.5px] min-[390px]:text-[17.5px] text-[#062A43] leading-tight">
              {title}
            </h3>
            <p className="font-ui text-[12.5px] min-[390px]:text-[13px] text-[#274A62] mt-0.5">
              {subtext}
            </p>
          </div>

          {/* Microphone Action Button */}
          <div className="w-[50px] h-[50px] min-[390px]:w-[54px] min-[390px]:h-[54px] rounded-full bg-[#CCE2F2] border border-[#B4D3EB] flex items-center justify-center shrink-0">
            <button
              type="button"
              onClick={onVoiceClick}
              aria-label="Ask ORCA with voice"
              className="w-[38px] h-[38px] min-[390px]:w-[40px] min-[390px]:h-[40px] rounded-full bg-[#062A43] text-white flex items-center justify-center shadow-sm hover:scale-105 active:scale-95 transition-transform duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40"
            >
              <Mic size={19} className="text-white stroke-[2.3]" />
            </button>
          </div>
        </div>

        {/* Suggestion Question Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <button
            type="button"
            onClick={() => onPromptClick?.(prompt1)}
            className="inline-flex items-center px-3 py-1.5 rounded-full bg-white text-[#062A43] border border-[#BCD8EC] font-ui font-medium text-[11px] min-[390px]:text-[11.5px] shadow-2xs hover:bg-[#F4F9FD] active:scale-98 transition-all cursor-pointer truncate max-w-full"
          >
            <span className="truncate">{prompt1}</span>
          </button>

          {prompt2 && (
            <button
              type="button"
              onClick={() => onPromptClick?.(prompt2)}
              className="inline-flex items-center px-3 py-1.5 rounded-full bg-white text-[#062A43] border border-[#BCD8EC] font-ui font-medium text-[11px] min-[390px]:text-[11.5px] shadow-2xs hover:bg-[#F4F9FD] active:scale-98 transition-all cursor-pointer truncate max-w-full"
            >
              <span className="truncate">{prompt2}</span>
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

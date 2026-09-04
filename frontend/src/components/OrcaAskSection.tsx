import React from 'react';
import { Mic } from 'lucide-react';
import { LanguageOption } from '../types';
import { getHomeTranslation } from '../data/homeTranslations';

interface OrcaAskSectionProps {
  currentLanguage?: LanguageOption;
  onVoiceClick?: () => void;
  onCardClick?: () => void;
  onSuggestionClick?: (question: string) => void;
}

// Symmetrical voice wave heights (audio frequency bars)
const LEFT_VOICE_BARS = [6, 12, 22, 14, 28, 18, 10];
const RIGHT_VOICE_BARS = [10, 18, 28, 14, 22, 12, 6];

/**
 * Authentic vertical voice-wave equalizer graphic
 * Series of vertical audio frequency bars with rounded caps
 */
const VoiceWaveBars: React.FC<{ bars: number[]; className?: string }> = ({
  bars,
  className = '',
}) => (
  <div
    className={`flex items-center gap-[3px] min-[390px]:gap-[4px] shrink-0 ${className}`}
    aria-hidden="true"
  >
    {bars.map((height, idx) => (
      <span
        key={idx}
        style={{ height: `${height}px` }}
        className="w-[2.5px] min-[390px]:w-[3px] rounded-full bg-[#356C92] shrink-0 transition-all duration-150"
      />
    ))}
  </div>
);

export const OrcaAskSection: React.FC<OrcaAskSectionProps> = ({
  currentLanguage,
  onVoiceClick,
  onCardClick,
  onSuggestionClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const homeTranslation = getHomeTranslation(langCode);
  const content = homeTranslation.ask;

  const handleCardClick = () => {
    if (onCardClick) {
      onCardClick();
    } else if (onVoiceClick) {
      onVoiceClick();
    }
  };

  return (
    <section
      className="relative w-full max-w-[1200px] mx-auto px-5 sm:px-6 md:px-8 -mt-8 sm:-mt-11 pb-10 sm:pb-14 select-none"
      id="orca-ask-section"
      aria-label="Ask ORCA Voice Assistant"
    >
      <div className="w-full max-w-[880px]">
        {/* 
          ===================================================================
          ASK ORCA CARD CONTAINER
          - Matching width of the 4 feature cards above
          - Flexible min-height ~180-192px ensuring multi-lingual text fits comfortably
          - Background: clearly visible soft marine blue tint (#E5F1F9)
          - Clear crisp border (#BCD8EC) and subtle shadow
          - Entire card is tappable with subtle interaction
          ===================================================================
        */}
        <div
          id="orca-ask-card"
          onClick={handleCardClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleCardClick();
            }
          }}
          aria-label={`Ask ORCA voice assistant card: ${content.title}. ${content.description}`}
          className="group relative w-full min-h-[180px] min-[390px]:min-h-[188px] sm:min-h-[196px] h-auto px-4 min-[390px]:px-4.5 sm:px-5 pt-3.5 min-[390px]:pt-4 sm:pt-4.5 pb-3 min-[390px]:pb-3.5 sm:pb-4 rounded-[18px] min-[390px]:rounded-[20px] bg-[#E5F1F9] border border-[#BCD8EC] shadow-[0_4px_16px_rgba(6,42,67,0.06)] hover:shadow-[0_8px_24px_rgba(6,42,67,0.09)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.99] transition-all duration-200 cursor-pointer flex flex-col justify-between items-stretch overflow-hidden focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#062A43]/30 gap-2.5"
        >
          {/* 
            -----------------------------------------------------------------
            TOP-LEFT: Title & Natural Wrapped Description
            - DM Sans
            - Title: bold/semibold, 16–18px, dark navy (#062A43)
            - Description: 11.5–12.5px, muted blue-gray (#274A62)
            - break-words and natural wrap prevents overflow in Indic scripts
            -----------------------------------------------------------------
          */}
          <div className="flex flex-col items-start z-10 w-full">
            <h2 className="font-ui font-semibold text-[16px] min-[390px]:text-[17.5px] sm:text-[19px] text-[#062A43] tracking-tight leading-tight break-words max-w-full">
              {content.title}
            </h2>
            <p className="font-ui font-normal text-[11.5px] min-[390px]:text-[12px] sm:text-[12.5px] text-[#274A62] leading-[1.3] mt-1 tracking-normal break-words max-w-[94%]">
              {content.description}
            </p>
          </div>

          {/* 
            -----------------------------------------------------------------
            MIDDLE: Voice Wave Bars + Centered Microphone
            - Authentic vertical voice frequency waveform bars on BOTH sides
            - Center microphone is the visual focal point:
              * Outer pale blue circular glow/ring (76–82px, #CCE2F2)
              * Inner dark navy circular button (48–54px, #062A43)
              * Crisp white microphone icon (24–26px)
            -----------------------------------------------------------------
          */}
          <div className="w-full flex items-center justify-center gap-3 min-[390px]:gap-4 sm:gap-5 my-auto z-10 py-0.5">
            {/* Left Voice Wave Bars */}
            <VoiceWaveBars bars={LEFT_VOICE_BARS} />

            {/* Microphone Button */}
            <div
              className="w-[72px] h-[72px] min-[390px]:w-[76px] min-[390px]:h-[76px] sm:w-[80px] sm:h-[80px] rounded-full bg-[#CCE2F2] border border-[#B4D3EB] flex items-center justify-center shrink-0 shadow-xs group-hover:scale-[1.02] transition-transform duration-150"
              aria-hidden="true"
            >
              <button
                type="button"
                id="orca-ask-mic-button"
                aria-label="Ask ORCA by voice"
                onClick={(e) => {
                  e.stopPropagation();
                  onVoiceClick?.();
                }}
                className="w-[46px] h-[46px] min-[390px]:w-[48px] min-[390px]:h-[48px] sm:w-[52px] sm:h-[52px] rounded-full bg-[#062A43] text-white flex items-center justify-center shadow-[0_3px_10px_rgba(6,42,67,0.25)] hover:scale-105 active:scale-95 transition-transform duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#062A43]/30"
              >
                <Mic size={22} className="text-white stroke-[2.3]" />
              </button>
            </div>

            {/* Right Voice Wave Bars (Mirrored) */}
            <VoiceWaveBars bars={RIGHT_VOICE_BARS} />
          </div>

          {/* 
            -----------------------------------------------------------------
            BOTTOM-CENTER: Suggestion Pill
            - Centered horizontally
            - Crisp white background (#FFFFFF) with refined border for high contrast
            - Dark navy text (#062A43)
            - DM Sans, 10–11.5px, medium weight
            - Fully rounded pill with truncate to prevent overflow
            -----------------------------------------------------------------
          */}
          <div className="w-full flex items-center justify-center z-10">
            <button
              type="button"
              id="orca-ask-suggestion-pill"
              onClick={(e) => {
                e.stopPropagation();
                onSuggestionClick?.(content.suggestion);
              }}
              aria-label={`Ask suggested question: ${content.suggestion}`}
              className="inline-flex items-center justify-center max-w-[94%] px-3.5 min-[390px]:px-4 py-1 min-[390px]:py-1.5 rounded-full bg-white text-[#062A43] border border-[#BCD8EC] font-ui font-medium text-[10.5px] min-[390px]:text-[11px] sm:text-[11.5px] tracking-normal shadow-2xs hover:bg-[#F4F9FD] active:scale-[0.98] transition-all duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/30"
            >
              <span className="truncate">{content.suggestion}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default OrcaAskSection;

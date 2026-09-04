import React from 'react';
import { Mic } from 'lucide-react';
import { AskTranslations } from '../../data/askData';

export type VoiceState = 'idle' | 'listening' | 'thinking';

interface OrcaVoiceCardProps {
  voiceState: VoiceState;
  onMicClick: () => void;
  translations: AskTranslations;
}

export const OrcaVoiceCard: React.FC<OrcaVoiceCardProps> = ({
  voiceState,
  onMicClick,
  translations,
}) => {
  const isListening = voiceState === 'listening';
  const isThinking = voiceState === 'thinking';

  return (
    <section
      className="w-full rounded-3xl p-6 min-[390px]:p-7 sm:p-8 bg-gradient-to-b from-[#F4F9FD] to-white border-2 border-[#CFE3F2] shadow-[0_4px_24px_rgba(6,42,67,0.06)] flex flex-col items-center justify-center text-center select-none transition-all duration-200"
      id="orca-voice-card"
      aria-label="Voice input area"
    >
      {/* Top prompt: "What do you want to know?" */}
      <h2
        className="font-ui font-bold text-[18px] min-[390px]:text-[20px] sm:text-[22px] text-[#062A43] tracking-tight leading-snug"
        id="orca-voice-prompt-title"
      >
        {isListening
          ? translations.listening
          : isThinking
          ? translations.thinking
          : translations.whatDoYouWantToKnow}
      </h2>

      {/* Subtext when listening/thinking */}
      {isListening ? (
        <p className="font-ui text-[13px] min-[390px]:text-[14px] text-[#1677A8] font-medium mt-1 animate-pulse">
          🎙️ “{translations.speakNow}”
        </p>
      ) : isThinking ? (
        <p className="font-ui text-[13px] min-[390px]:text-[14px] text-[#557186] font-medium mt-1 animate-pulse">
          {translations.checkingConditions}
        </p>
      ) : (
        <div className="h-[21px] mt-1" aria-hidden="true" />
      )}

      {/* 
        ===================================================================
        LARGE MICROPHONE BUTTON
        - Dark navy circular center (#062A43 or #06365A)
        - White microphone icon
        - Soft pale-blue outer circle/glow
        - Approximately 88–96px total diameter
        - Centered horizontally
        - Largest interactive element on the page
        - Subtle pulsing rings when listening
        ===================================================================
      */}
      <div className="relative mt-5 sm:mt-6 mb-4 flex items-center justify-center">
        {/* Animated pulse rings when listening */}
        {isListening && (
          <>
            <span
              className="absolute -inset-4 rounded-full bg-[#1677A8]/15 animate-ping duration-1000"
              aria-hidden="true"
            />
            <span
              className="absolute -inset-8 rounded-full bg-[#1677A8]/10 animate-pulse duration-700"
              aria-hidden="true"
            />
          </>
        )}

        {/* Soft pale-blue outer glow circle */}
        <div
          className={`w-[96px] h-[96px] min-[390px]:w-[104px] min-[390px]:h-[104px] rounded-full flex items-center justify-center p-2.5 transition-all duration-300 ${
            isListening
              ? 'bg-[#BAE6FD]/80 shadow-[0_0_24px_rgba(22,119,168,0.35)] scale-105'
              : 'bg-[#D9EEFB] hover:bg-[#CCE7F8]'
          }`}
        >
          {/* Dark Navy Circular Center (80px) */}
          <button
            type="button"
            onClick={onMicClick}
            id="orca-voice-mic-btn"
            aria-label="Ask ORCA by voice"
            className={`w-full h-full rounded-full flex items-center justify-center transition-all duration-200 cursor-pointer shadow-md active:scale-95 focus:outline-hidden focus-visible:ring-4 focus-visible:ring-[#062A43]/40 ${
              isListening
                ? 'bg-[#DC2626] text-white animate-pulse'
                : 'bg-[#062A43] hover:bg-[#06365A] text-white'
            }`}
          >
            <Mic
              size={36}
              className={`stroke-[2.4] ${isListening ? 'animate-bounce' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Label below microphone: "Tap to speak" */}
      <span
        className={`font-ui text-[14px] min-[390px]:text-[15px] font-semibold tracking-tight transition-colors ${
          isListening
            ? 'text-[#DC2626] font-bold'
            : isThinking
            ? 'text-[#1677A8]'
            : 'text-[#557186]'
        }`}
      >
        {isListening
          ? translations.listening
          : isThinking
          ? translations.thinking
          : translations.tapToSpeak}
      </span>
    </section>
  );
};

import React from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { AskTranslations } from '../../data/askData';

export type VoiceState = 'idle' | 'listening' | 'thinking';

interface OrcaVoiceCardProps {
  voiceState: VoiceState;
  onMicClick: () => void;
  translations: AskTranslations;
  /** Live input loudness 0..1 while recording. */
  level?: number;
}

/** Twelve bars around the button, so loudness reads as a ring rather than a number. */
const BAR_COUNT = 12;

export const OrcaVoiceCard: React.FC<OrcaVoiceCardProps> = ({
  voiceState,
  onMicClick,
  translations,
  level = 0,
}) => {
  const isListening = voiceState === 'listening';
  const isThinking = voiceState === 'thinking';

  // Keep a floor so the ring still breathes during natural pauses in speech.
  const energy = isListening ? Math.max(0.12, Math.min(1, level)) : 0;

  return (
    <section
      className="w-full rounded-3xl p-6 min-[390px]:p-7 sm:p-8 bg-gradient-to-b from-[#F4F9FD] to-white border-2 border-[#CFE3F2] shadow-[0_4px_24px_rgba(6,42,67,0.06)] flex flex-col items-center justify-center text-center select-none transition-all duration-200"
      id="orca-voice-card"
      aria-label="Voice input area"
    >
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

      {isListening ? (
        <p className="font-ui text-[13px] min-[390px]:text-[14px] text-[#1677A8] font-medium mt-1">
          “{translations.speakNow}”
        </p>
      ) : isThinking ? (
        <p className="font-ui text-[13px] min-[390px]:text-[14px] text-[#557186] font-medium mt-1 animate-pulse">
          {translations.checkingConditions}
        </p>
      ) : (
        <div className="h-[21px] mt-1" aria-hidden="true" />
      )}

      <div className="relative mt-6 sm:mt-7 mb-5 flex items-center justify-center w-[168px] h-[168px]">
        {/*
          The rings and bars below are driven by real microphone loudness, not a
          timer. That makes the animation double as proof the microphone is
          actually picking the user up — the thing they cannot otherwise tell
          until the transcript comes back.
        */}
        {isListening && (
          <>
            <span
              aria-hidden="true"
              className="absolute rounded-full bg-[#1677A8]/10 transition-transform duration-100 ease-out"
              style={{
                width: 168,
                height: 168,
                transform: `scale(${0.62 + energy * 0.38})`,
              }}
            />
            <span
              aria-hidden="true"
              className="absolute rounded-full bg-[#1677A8]/15 transition-transform duration-75 ease-out"
              style={{
                width: 140,
                height: 140,
                transform: `scale(${0.68 + energy * 0.3})`,
              }}
            />

            {/* Radial level bars */}
            <svg
              className="absolute w-[168px] h-[168px] -rotate-90 pointer-events-none"
              viewBox="0 0 168 168"
              aria-hidden="true"
            >
              {Array.from({ length: BAR_COUNT }).map((_, i) => {
                const angle = (i / BAR_COUNT) * Math.PI * 2;
                // Vary each bar a little so the ring looks alive, not uniform.
                const jitter = 0.75 + 0.25 * Math.abs(Math.sin(i * 1.7));
                const inner = 60;
                const len = 6 + energy * 22 * jitter;
                const cx = 84 + Math.cos(angle) * inner;
                const cy = 84 + Math.sin(angle) * inner;
                const ex = 84 + Math.cos(angle) * (inner + len);
                const ey = 84 + Math.sin(angle) * (inner + len);
                return (
                  <line
                    key={i}
                    x1={cx}
                    y1={cy}
                    x2={ex}
                    y2={ey}
                    stroke="#1677A8"
                    strokeOpacity={0.35 + energy * 0.45}
                    strokeWidth={3}
                    strokeLinecap="round"
                  />
                );
              })}
            </svg>
          </>
        )}

        {isThinking && (
          <span
            aria-hidden="true"
            className="absolute w-[124px] h-[124px] rounded-full border-2 border-[#BAE6FD] border-t-[#1677A8] animate-spin"
            style={{ animationDuration: '1.1s' }}
          />
        )}

        <div
          className={`relative w-[96px] h-[96px] min-[390px]:w-[104px] min-[390px]:h-[104px] rounded-full flex items-center justify-center p-2.5 transition-all duration-300 ${
            isListening
              ? 'bg-[#FEE2E2]/90 shadow-[0_0_28px_rgba(220,38,38,0.28)]'
              : 'bg-[#D9EEFB] hover:bg-[#CCE7F8]'
          }`}
        >
          <button
            type="button"
            onClick={onMicClick}
            disabled={isThinking}
            id="orca-voice-mic-btn"
            aria-label={isListening ? 'Stop recording' : 'Ask ORCA by voice'}
            aria-pressed={isListening}
            className={`w-full h-full rounded-full flex items-center justify-center transition-all duration-200 cursor-pointer shadow-md active:scale-95 focus:outline-hidden focus-visible:ring-4 focus-visible:ring-[#062A43]/40 disabled:cursor-not-allowed ${
              isListening
                ? 'bg-[#DC2626] text-white'
                : isThinking
                  ? 'bg-[#94A3B8] text-white'
                  : 'bg-[#062A43] hover:bg-[#06365A] text-white'
            }`}
            style={
              isListening
                ? { transform: `scale(${1 + energy * 0.07})`, transition: 'transform 80ms ease-out' }
                : undefined
            }
          >
            {isThinking ? (
              <Loader2 size={32} className="stroke-[2.4] animate-spin" />
            ) : isListening ? (
              <Square size={30} className="stroke-[2.6] fill-current" />
            ) : (
              <Mic size={36} className="stroke-[2.4]" />
            )}
          </button>
        </div>
      </div>

      <span
        className={`font-ui text-[14px] min-[390px]:text-[15px] font-semibold tracking-tight transition-colors ${
          isListening ? 'text-[#DC2626] font-bold' : isThinking ? 'text-[#1677A8]' : 'text-[#557186]'
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

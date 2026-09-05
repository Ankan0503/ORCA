import React, { useState, useEffect, useRef } from 'react';
import { Volume2, ChevronDown, ChevronUp, RotateCcw, ArrowRight } from 'lucide-react';
import { AskTranslations } from '../../data/askData';
import { speak } from '../../services/orcaApi';

interface OrcaAnswerCardProps {
  userQuestion: string;
  orcaAnswer: string;
  actionLabel?: string;
  actionRoute?: 'find-fish' | 'safety' | 'sea-today' | 'alerts';
  whyExplanation?: string;
  onNavigateAction?: (route: 'find-fish' | 'safety' | 'sea-today' | 'alerts') => void;
  onReset?: () => void;
  translations: AskTranslations;
  /** Audio already returned with the answer, so replaying costs no extra call. */
  answerAudioUrl?: string | null;
  /** Language the answer is written in, used when synthesising on demand. */
  answerLanguage?: string;
}

export const OrcaAnswerCard: React.FC<OrcaAnswerCardProps> = ({
  userQuestion,
  orcaAnswer,
  actionLabel,
  actionRoute,
  whyExplanation,
  onNavigateAction,
  onReset,
  translations,
  answerAudioUrl,
  answerLanguage = 'en',
}) => {
  const [showWhy, setShowWhy] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Synthesised audio is cached so tapping Listen twice does not re-call the API.
  const cachedUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
      if (cachedUrlRef.current) URL.revokeObjectURL(cachedUrlRef.current);
    };
  }, []);

  /**
   * Speaks the answer with Sarvam's Indian-language voices. The browser's own
   * speechSynthesis is not used: on most devices it has no Indic voices at all
   * and reads Bengali or Tamil with an English voice.
   */
  const handleSpeakAloud = async () => {
    if (isSpeaking) {
      audioRef.current?.pause();
      setIsSpeaking(false);
      return;
    }

    try {
      let url = answerAudioUrl ?? cachedUrlRef.current;
      if (!url) {
        url = await speak(orcaAnswer, answerLanguage);
        cachedUrlRef.current = url;
      }

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => setIsSpeaking(false);
      setIsSpeaking(true);
      await audio.play();
    } catch {
      setIsSpeaking(false);
    }
  };

  return (
    <section
      className="w-full rounded-3xl p-5 min-[390px]:p-6 sm:p-7 bg-white border-2 border-[#BCD8EC] shadow-[0_6px_24px_rgba(6,42,67,0.08)] flex flex-col gap-4 select-none animate-fade-in"
      id="orca-answer-card"
      aria-label="ORCA conversational answer"
    >
      {/* 
        1. USER QUESTION HEADER
        Fisherman: "Where should I fish today?"
      */}
      <div className="flex items-start justify-between gap-3 border-b border-[#EDF4F9] pb-3">
        <div className="flex flex-col min-w-0">
          <span className="font-ui text-[11.5px] font-extrabold uppercase tracking-wider text-[#71869A]">
            {translations.youLabel}
          </span>
          <p className="font-ui font-bold text-[15px] min-[390px]:text-[16px] text-[#062A43] mt-0.5">
            “{userQuestion}”
          </p>
        </div>

        {/* Reset / Ask another button */}
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            id="orca-answer-reset-btn"
            aria-label="Ask another question"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F4F9FD] border border-[#D5E5F0] text-[#557186] hover:text-[#062A43] hover:bg-[#E8F3FA] text-[12px] font-ui font-medium transition-colors shrink-0 cursor-pointer"
          >
            <RotateCcw size={12} />
            <span className="hidden min-[390px]:inline">{translations.askAnother}</span>
          </button>
        )}
      </div>

      {/* 
        2. ORCA RESPONSE
        ORCA:
        “Try the green area, 12 km offshore.
        Sea conditions are safe.”
      */}
      <div className="flex flex-col items-start gap-1">
        <div className="w-full flex items-center justify-between gap-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[#E5F1F9] text-[#06365A] font-ui text-[12px] font-bold tracking-tight">
            <span>🐳</span>
            <span>{translations.orcaLabel}</span>
          </div>

          {/* Read aloud audio button */}
          <button
            type="button"
            onClick={handleSpeakAloud}
            id="orca-read-aloud-btn"
            aria-label={isSpeaking ? 'Stop speaking' : 'Read answer aloud'}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[12px] font-ui font-semibold transition-all cursor-pointer ${
              isSpeaking
                ? 'bg-[#1677A8] text-white border-[#1677A8] animate-pulse'
                : 'bg-[#F0F7FB] hover:bg-[#E3EFF7] text-[#1677A8] border-[#CFE3F2]'
            }`}
          >
            <Volume2 size={13} className="stroke-[2.5]" />
            <span>{isSpeaking ? 'Speaking…' : translations.listenAnswer}</span>
          </button>
        </div>

        {/* Large, clear answer text formatted with generous spacing */}
        <div className="mt-2.5 w-full">
          <p className="font-ui font-extrabold text-[20px] min-[390px]:text-[22px] sm:text-[24px] text-[#062A43] leading-[1.3] tracking-tight">
            “{orcaAnswer}”
          </p>
        </div>
      </div>

      {/* 
        3. ACTIONS:
        - Primary Action Button: "View spot →" / "Check safety →"
        - "Why this spot?" button (reveals simple reason)
      */}
      <div className="pt-2 flex flex-col gap-2.5 w-full">
        {actionLabel && actionRoute && onNavigateAction && (
          <button
            type="button"
            onClick={() => onNavigateAction(actionRoute)}
            id="orca-answer-action-btn"
            className="w-full py-3 min-[390px]:py-3.5 px-4 rounded-xl min-[390px]:rounded-2xl bg-[#062A43] hover:bg-[#06365A] active:scale-[0.99] text-white font-ui font-bold text-[15px] min-[390px]:text-[16px] shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#062A43]/40"
          >
            <span>{actionLabel}</span>
            <ArrowRight size={18} className="stroke-[2.5]" />
          </button>
        )}

        {/* Optional "Why this spot?" / "Why?" toggle button */}
        {whyExplanation && (
          <div className="w-full flex flex-col items-stretch">
            <button
              type="button"
              onClick={() => setShowWhy(!showWhy)}
              id="orca-why-toggle-btn"
              aria-expanded={showWhy}
              className="inline-flex items-center justify-center gap-1.5 py-1.5 text-center text-[#1677A8] hover:text-[#062A43] font-ui font-bold text-[13px] min-[390px]:text-[13.5px] transition-colors cursor-pointer"
            >
              <span>{translations.whyThisSpot}</span>
              {showWhy ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>

            {showWhy && (
              <div
                id="orca-why-explanation"
                className="mt-1.5 p-3 rounded-xl bg-[#F0F7FB] border border-[#D5E5F0] text-[13px] min-[390px]:text-[13.5px] text-[#274A62] font-ui leading-relaxed animate-fade-in"
              >
                {whyExplanation}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

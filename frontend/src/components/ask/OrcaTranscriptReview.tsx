import React, { useEffect, useRef, useState } from 'react';
import { Check, Mic, Pencil } from 'lucide-react';
import { AskTranslations } from '../../data/askData';

interface OrcaTranscriptReviewProps {
  transcript: string;
  /** Language identified from the speech, shown so the user can see it was understood. */
  languageLabel?: string;
  /** True when the language guess was shaky, so the user checks it rather than trusting it. */
  lowConfidence?: boolean;
  onSend: (finalText: string) => void;
  onSpeakAgain: () => void;
  translations: AskTranslations;
}

/**
 * The step between speaking and answering.
 *
 * Speech recognition mishears things, and planning plus four agents is the slow
 * part of a turn. Showing what was heard first means a wrong word costs one
 * correction instead of a whole wasted round trip — and the user can fix it in
 * place rather than repeating the whole question.
 */
export const OrcaTranscriptReview: React.FC<OrcaTranscriptReviewProps> = ({
  transcript,
  languageLabel,
  lowConfidence = false,
  onSend,
  onSpeakAgain,
  translations,
}) => {
  const [text, setText] = useState(transcript);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setText(transcript);
  }, [transcript]);

  // Grow with the content so long questions are fully visible.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  const canSend = text.trim().length > 0;

  return (
    <section
      className="w-full rounded-3xl p-5 min-[390px]:p-6 bg-white border-2 border-[#BAE6FD] shadow-[0_6px_24px_rgba(6,42,67,0.08)] flex flex-col gap-3 select-none animate-fade-in"
      id="orca-transcript-review"
      aria-label="Check what ORCA heard"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-ui text-[11.5px] font-extrabold uppercase tracking-wider text-[#1677A8]">
          {translations.heardThis}
        </span>
        {languageLabel && (
          <span
            className={`font-ui text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              lowConfidence ? 'bg-[#FEF3C7] text-[#92400E]' : 'bg-[#E0F2FE] text-[#0369A1]'
            }`}
          >
            {languageLabel}
          </span>
        )}
      </div>

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={1}
        aria-label={translations.heardThis}
        className="w-full resize-none bg-transparent font-ui font-semibold text-[17px] min-[390px]:text-[18px] leading-snug text-[#062A43] outline-none border-b-2 border-dashed border-[#CFE3F2] focus:border-[#1677A8] pb-1.5"
      />

      <p className="flex items-center gap-1.5 font-ui text-[12px] text-[#71869A]">
        <Pencil size={12} className="shrink-0" />
        {lowConfidence ? translations.lowConfidence : translations.editIfWrong}
      </p>

      <div className="flex items-center gap-2.5 mt-1">
        <button
          type="button"
          onClick={onSpeakAgain}
          className="flex items-center justify-center gap-1.5 h-[46px] px-4 rounded-full border-2 border-[#CFE3F2] bg-white text-[#274A62] font-ui font-semibold text-[14px] cursor-pointer transition-colors hover:bg-[#F4F9FD] active:scale-98 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1677A8]"
        >
          <Mic size={17} className="stroke-[2.4]" />
          {translations.speakAgain}
        </button>

        <button
          type="button"
          onClick={() => canSend && onSend(text.trim())}
          disabled={!canSend}
          className="flex-1 flex items-center justify-center gap-2 h-[46px] rounded-full bg-[#062A43] text-white font-ui font-bold text-[15px] cursor-pointer transition-all hover:bg-[#06365A] active:scale-98 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-4 focus-visible:ring-[#062A43]/40"
        >
          <Check size={18} className="stroke-[2.6]" />
          {translations.sendQuestion}
        </button>
      </div>
    </section>
  );
};

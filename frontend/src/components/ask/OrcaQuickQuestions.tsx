import React from 'react';
import { QuickQuestion } from '../../data/askData';

interface OrcaQuickQuestionsProps {
  questions: QuickQuestion[];
  onSelectQuestion: (question: QuickQuestion) => void;
  title?: string;
}

export const OrcaQuickQuestions: React.FC<OrcaQuickQuestionsProps> = ({
  questions,
  onSelectQuestion,
  title = 'Try asking',
}) => {
  return (
    <section
      className="w-full flex flex-col gap-2.5 sm:gap-3 select-none"
      id="orca-quick-questions-section"
      aria-label="Quick suggested questions"
    >
      {/* "Try asking" label */}
      <h3 className="font-ui font-semibold text-[14px] min-[390px]:text-[15px] text-[#557186] px-1 tracking-tight">
        {title}
      </h3>

      {/* 
        4 Simple Question Buttons in 2x2 grid
        🎣 “Where should I fish?”
        🛡️ “Is it safe today?”
        🌊 “How is the sea?”
        ⚠️ “Any warnings?”
      */}
      <div className="grid grid-cols-2 gap-2.5 min-[390px]:gap-3 w-full">
        {questions.map((q) => (
          <button
            key={q.id}
            type="button"
            onClick={() => onSelectQuestion(q)}
            id={`quick-question-${q.id}`}
            aria-label={`Ask ORCA: ${q.question}`}
            className="group flex items-center gap-2.5 p-3 min-[390px]:p-3.5 min-h-[50px] min-[390px]:min-h-[54px] rounded-2xl bg-white/95 backdrop-blur-xs border border-[#D5E5F0] hover:border-[#96C7EA] hover:bg-[#F3F9FD] shadow-xs hover:shadow-sm active:scale-[0.98] transition-all duration-150 text-left cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/30"
          >
            {/* Emoji icon */}
            <span
              className="text-[18px] min-[390px]:text-[20px] shrink-0 leading-none group-hover:scale-110 transition-transform duration-150"
              aria-hidden="true"
            >
              {q.icon}
            </span>

            {/* Question Text */}
            <span className="font-ui font-bold text-[13px] min-[390px]:text-[13.5px] sm:text-[14px] text-[#062A43] leading-snug break-words">
              “{q.question}”
            </span>
          </button>
        ))}
      </div>
    </section>
  );
};

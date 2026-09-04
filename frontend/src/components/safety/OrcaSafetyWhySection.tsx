import React from 'react';
import { SafetyData } from '../../data/safetyData';

interface OrcaSafetyWhySectionProps {
  data: SafetyData;
  whyTitle?: string;
}

export const OrcaSafetyWhySection: React.FC<OrcaSafetyWhySectionProps> = ({
  data,
  whyTitle = 'Why?',
}) => {
  const isSafe = data.status === 'safe';
  const isCaution = data.status === 'caution';

  return (
    <section
      className="w-full mt-4 sm:mt-5 bg-white rounded-[20px] sm:rounded-[22px] p-4.5 min-[390px]:p-5 sm:p-6 border border-[#D8E6F0] shadow-[0_3px_12px_rgba(6,42,67,0.04)] select-none"
      id="orca-safety-why-section"
      aria-label="Explainability reason"
    >
      {/* Section Heading: "Why?" */}
      <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] sm:text-[19px] text-[#062A43] tracking-tight flex items-center gap-2">
        <span>{whyTitle}</span>
      </h3>

      {/* 
        3–4 Small Evidence Chips:
        - Quick visual confirmation
        - High contrast tags
        - Green for safe, Amber for caution, Rose for danger
      */}
      <div className="w-full flex flex-wrap items-center gap-2 mt-2.5 sm:mt-3">
        {data.evidenceChips.map((chip, index) => {
          const isNegative = chip.startsWith('✕');
          const isWarning = chip.startsWith('⚠️');

          const chipStyle = isNegative
            ? 'bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]'
            : isWarning
            ? 'bg-[#FEF0C7] text-[#92400E] border-[#FCD34D]'
            : 'bg-[#EBF7EE] text-[#166534] border-[#C9EBD2]';

          return (
            <span
              key={index}
              className={`inline-flex items-center px-3 py-1 rounded-full text-[12px] min-[390px]:text-[12.5px] font-semibold border ${chipStyle} shadow-2xs whitespace-nowrap`}
            >
              {chip}
            </span>
          );
        })}
      </div>
    </section>
  );
};

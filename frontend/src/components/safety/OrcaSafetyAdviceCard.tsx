import React from 'react';
import { Compass, Check, AlertCircle } from 'lucide-react';
import { SafetyData } from '../../data/safetyData';

interface OrcaSafetyAdviceCardProps {
  data: SafetyData;
  title?: string;
}

export const OrcaSafetyAdviceCard: React.FC<OrcaSafetyAdviceCardProps> = ({
  data,
  title = 'What should I do?',
}) => {
  const isSafe = data.status === 'safe';
  const isCaution = data.status === 'caution';

  return (
    <section
      className="w-full mt-6 select-none"
      id="orca-safety-advice-section"
      aria-label="Practical fisherman advice"
    >
      <div className="w-full rounded-[20px] bg-white p-4.5 min-[390px]:p-5 sm:p-6 border border-[#D8E6F0] shadow-[0_3px_12px_rgba(6,42,67,0.04)] flex flex-col gap-3">
        {/* Header with action icon */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-[#E5F1F9] border border-[#BCD8EC] flex items-center justify-center shrink-0">
            <Compass size={17} className="text-[#1677A8]" />
          </div>
          <h3 className="font-ui font-bold text-[17.5px] min-[390px]:text-[18.5px] text-[#062A43] tracking-tight">
            {title}
          </h3>
        </div>

        {/* 3 Clear Action Steps */}
        <div className="flex flex-col gap-2.5 pt-1">
          {data.actionSteps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-2.5">
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                  isSafe
                    ? 'bg-[#EBF7EE] text-[#16A34A]'
                    : isCaution
                    ? 'bg-[#FEF0C7] text-[#D97706]'
                    : 'bg-[#FEE2E2] text-[#DC2626]'
                }`}
              >
                <Check size={12} className="stroke-[3]" />
              </span>
              <span className="font-ui text-[13px] min-[390px]:text-[13.5px] text-[#274A62] font-medium leading-snug">
                {step}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

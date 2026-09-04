import React from 'react';
import { Wind, Waves, CloudRain, Eye } from 'lucide-react';
import { SeaTodayCondition } from '../../data/seaTodayData';

interface OrcaSeaTodayConditionsProps {
  conditions: SeaTodayCondition[];
  title?: string;
}

export const OrcaSeaTodayConditions: React.FC<OrcaSeaTodayConditionsProps> = ({
  conditions,
  title = 'Today',
}) => {
  const renderIcon = (iconType: string) => {
    switch (iconType) {
      case 'wind':
        return <Wind size={22} className="text-[#0284C7] stroke-[2.3]" />;
      case 'waves':
        return <Waves size={22} className="text-[#0D9488] stroke-[2.3]" />;
      case 'rain':
        return <CloudRain size={22} className="text-[#6366F1] stroke-[2.3]" />;
      case 'visibility':
        return <Eye size={22} className="text-[#EAB308] stroke-[2.3]" />;
      default:
        return <Waves size={22} className="text-[#0284C7] stroke-[2.3]" />;
    }
  };

  const getStatusBadgeStyle = (statusType: 'good' | 'caution' | 'alert') => {
    switch (statusType) {
      case 'good':
        return 'bg-[#DCFCE7] text-[#15803D] border-[#BBF7D0]';
      case 'caution':
        return 'bg-[#FEF9C3] text-[#854D0E] border-[#FEF08A]';
      case 'alert':
        return 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
      default:
        return 'bg-[#F1F5F9] text-[#334155] border-[#E2E8F0]';
    }
  };

  return (
    <section
      className="w-full flex flex-col gap-3 select-none"
      id="orca-sea-today-conditions-section"
      aria-label="Important sea conditions"
    >
      {/* Section Title: "Today" */}
      <div className="flex items-center justify-between px-1">
        <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight">
          {title}
        </h3>
      </div>

      {/* 
        2 × 2 Grid with exactly 4 condition cards:
        1. Wind (12 km/h - Moderate)
        2. Waves (0.8 m - Calm)
        3. Rain (0 mm - No rain)
        4. Visibility (10+ km - Good)
      */}
      <div className="grid grid-cols-2 gap-3 min-[390px]:gap-3.5 sm:gap-4 w-full">
        {conditions.map((item) => (
          <div
            key={item.id}
            id={`condition-card-${item.id}`}
            className="p-3.5 min-[390px]:p-4 sm:p-5 rounded-2xl bg-white/95 backdrop-blur-sm border border-[#D7E5EE] shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow duration-150"
          >
            {/* Top row: Icon + Condition Name */}
            <div className="flex items-center justify-between gap-2">
              <span className="font-ui font-medium text-[13.5px] min-[390px]:text-[14px] text-[#557186]">
                {item.name}
              </span>
              <div className="w-8 h-8 rounded-xl bg-[#F0F6FA] flex items-center justify-center shrink-0">
                {renderIcon(item.icon)}
              </div>
            </div>

            {/* Large Value */}
            <div className="mt-2.5 sm:mt-3">
              <span className="font-display font-bold text-[24px] min-[390px]:text-[26px] sm:text-[28px] text-[#062A43] leading-none tracking-tight block">
                {item.value}
              </span>
            </div>

            {/* One-word status pill */}
            <div className="mt-2 sm:mt-2.5 flex items-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full border text-[11.5px] min-[390px]:text-[12px] font-ui font-bold ${getStatusBadgeStyle(
                  item.statusType
                )}`}
              >
                {item.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

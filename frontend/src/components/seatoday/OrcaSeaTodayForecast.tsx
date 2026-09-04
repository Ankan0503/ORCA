import React from 'react';
import { ForecastHour } from '../../data/seaTodayData';

interface OrcaSeaTodayForecastProps {
  forecast: ForecastHour[];
  title?: string;
}

export const OrcaSeaTodayForecast: React.FC<OrcaSeaTodayForecastProps> = ({
  forecast,
  title = 'Today',
}) => {
  return (
    <section
      className="w-full flex flex-col gap-2.5 sm:gap-3 select-none"
      id="orca-sea-today-forecast-section"
      aria-label="Today's simple sea forecast"
    >
      {/* Title */}
      <div className="flex items-center justify-between px-1">
        <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight">
          {title}
        </h3>
      </div>

      {/* 
        Glanceable Horizontal Forecast Row:
        - 6 AM (🌤 27° Calm)
        - 9 AM (☀️ 28° Calm)
        - 12 PM (🌤 28° Calm)
        - 3 PM (🌊 27° Slight waves)
        - 6 PM (☀️ 26° Calm)
      */}
      <div
        className="w-full grid grid-cols-5 gap-1.5 min-[390px]:gap-2 sm:gap-3"
        role="region"
        aria-label="Hourly Sea Condition Forecast"
      >
        {forecast.map((item, index) => (
          <div
            key={index}
            className={`p-2 min-[390px]:p-2.5 sm:p-3.5 rounded-xl sm:rounded-2xl border flex flex-col items-center justify-between text-center transition-all ${
              item.condition.includes('Rough') || item.condition.includes('High')
                ? 'bg-[#FEF2F2] border-[#FCA5A5]'
                : item.condition.includes('waves') || item.condition.includes('Choppy')
                ? 'bg-[#FEFCE8] border-[#FDE047]'
                : 'bg-white/95 border-[#D8E6F0]'
            }`}
          >
            {/* Time: 6 AM, 9 AM, etc. */}
            <span className="font-ui font-bold text-[11px] min-[390px]:text-[12px] sm:text-[13px] text-[#557186] tracking-tight whitespace-nowrap">
              {item.time}
            </span>

            {/* Weather / Wave Icon */}
            <div className="my-1.5 text-xl min-[390px]:text-2xl sm:text-3xl" aria-hidden="true">
              {item.icon}
            </div>

            {/* Temperature: 27°, 28° */}
            <span className="font-display font-bold text-[15px] min-[390px]:text-[16px] sm:text-[18px] text-[#062A43] leading-none">
              {item.temp}
            </span>

            {/* Condition: Calm / Slight waves */}
            <span
              className={`font-ui font-bold text-[9.5px] min-[390px]:text-[10.5px] sm:text-[11.5px] mt-1 line-clamp-1 leading-tight ${
                item.condition.includes('Rough') || item.condition.includes('High')
                  ? 'text-[#DC2626]'
                  : item.condition.includes('waves') || item.condition.includes('Choppy')
                  ? 'text-[#A16207]'
                  : 'text-[#15803D]'
              }`}
            >
              {item.condition}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};

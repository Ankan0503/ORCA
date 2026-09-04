import React, { useState } from 'react';
import { Info, ChevronDown, ChevronUp } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';

interface OrcaMapLegendProps {
  translations: MapTranslations;
}

export const OrcaMapLegend: React.FC<OrcaMapLegendProps> = ({ translations }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <aside
      className="absolute top-[136px] sm:top-[144px] left-2.5 sm:left-4 z-20 pointer-events-auto select-none max-w-[170px] sm:max-w-[190px]"
      id="orca-map-legend"
      aria-label="Map color legend"
    >
      <div className="bg-white/95 backdrop-blur-md border border-[#D0DFEB] rounded-2xl shadow-md p-2 sm:p-2.5 flex flex-col gap-1.5 transition-all">
        {/* Toggle header */}
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          id="orca-map-legend-toggle"
          aria-expanded={isExpanded}
          className="flex items-center justify-between gap-1 w-full text-left font-ui font-bold text-[11px] min-[390px]:text-[11.5px] uppercase tracking-wider text-[#557186] cursor-pointer hover:text-[#062A43] focus:outline-hidden"
        >
          <span className="flex items-center gap-1">
            <Info size={13} className="text-[#1677A8]" />
            <span>Legend</span>
          </span>
          {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {/* Legend items */}
        {isExpanded && (
          <ul className="flex flex-col gap-1 mt-0.5" role="list">
            <li className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#16A34A] shrink-0 border border-white shadow-2xs" />
              <span className="font-ui font-semibold text-[11.5px] min-[390px]:text-[12px] text-[#062A43] leading-none">
                {translations.legend.best}
              </span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#EAB308] shrink-0 border border-white shadow-2xs" />
              <span className="font-ui font-semibold text-[11.5px] min-[390px]:text-[12px] text-[#062A43] leading-none">
                {translations.legend.good}
              </span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#DC2626] shrink-0 border border-white shadow-2xs" />
              <span className="font-ui font-semibold text-[11.5px] min-[390px]:text-[12px] text-[#062A43] leading-none">
                {translations.legend.avoid}
              </span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#CBD5E1] shrink-0 border-2 border-dashed border-[#64748B] shadow-2xs" />
              <span className="font-ui font-semibold text-[11.5px] min-[390px]:text-[12px] text-[#062A43] leading-none">
                {translations.legend.restricted}
              </span>
            </li>
          </ul>
        )}
      </div>
    </aside>
  );
};

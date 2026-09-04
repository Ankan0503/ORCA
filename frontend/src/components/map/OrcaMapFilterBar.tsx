import React from 'react';
import { MapFilter, MapTranslations } from '../../data/mapData';

export type MapFilterType = 'fishing' | 'safety' | 'pfz' | 'restrictions';

interface OrcaMapFilterBarProps {
  activeFilter: MapFilterType;
  onChangeFilter: (filter: MapFilterType) => void;
  translations: MapTranslations;
}

export const OrcaMapFilterBar: React.FC<OrcaMapFilterBarProps> = ({
  activeFilter,
  onChangeFilter,
  translations,
}) => {
  const filters: { id: MapFilterType; label: string; icon: string }[] = [
    { id: 'fishing', label: translations.filters.fishing, icon: '🎣' },
    { id: 'safety', label: translations.filters.safety, icon: '🛡️' },
    { id: 'pfz', label: translations.filters.pfz, icon: '🌊' },
    { id: 'restrictions', label: translations.filters.restrictions, icon: '🚫' },
  ];

  return (
    <nav
      className="absolute top-[82px] sm:top-[88px] left-2.5 sm:left-4 right-2.5 sm:right-4 z-20 pointer-events-auto flex items-center justify-start gap-1.5 overflow-x-auto pb-1 no-scrollbar select-none"
      id="orca-map-filter-bar"
      aria-label="Map filters"
    >
      <div className="flex items-center gap-1.5 bg-white/90 backdrop-blur-md p-1 rounded-full border border-[#D0DFEB] shadow-md">
        {filters.map((f) => {
          const isSelected = activeFilter === f.id;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => onChangeFilter(f.id)}
              id={`map-filter-btn-${f.id}`}
              aria-pressed={isSelected}
              className={`min-h-[38px] px-3 sm:px-3.5 py-1.5 rounded-full font-ui text-[12.5px] min-[390px]:text-[13px] font-bold tracking-tight whitespace-nowrap flex items-center gap-1.5 transition-all duration-150 cursor-pointer active:scale-95 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/40 ${
                isSelected
                  ? 'bg-[#062A43] text-white shadow-sm'
                  : 'bg-transparent text-[#274A62] hover:bg-[#EAF3FA] hover:text-[#062A43]'
              }`}
            >
              <span className="text-[13px] leading-none" aria-hidden="true">
                {f.icon}
              </span>
              <span>{f.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

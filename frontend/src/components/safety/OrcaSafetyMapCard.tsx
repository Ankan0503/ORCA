import React from 'react';
import { ArrowRight, MapPin, Compass } from 'lucide-react';
import { SafetyStatus } from '../../data/safetyData';

interface OrcaSafetyMapCardProps {
  status: SafetyStatus;
  title?: string;
  subtext?: string;
  viewFullMapText?: string;
  safeLegend?: string;
  cautionLegend?: string;
  dangerLegend?: string;
  onViewFullMap?: () => void;
}

export const OrcaSafetyMapCard: React.FC<OrcaSafetyMapCardProps> = ({
  status,
  title = 'Safe area near you',
  subtext = 'Stay within the green area for safe navigation',
  viewFullMapText = 'View full map →',
  safeLegend = 'Safe zone (0–15 km)',
  cautionLegend = 'Caution zone (15–30 km)',
  dangerLegend = 'Danger zone (>30 km)',
  onViewFullMap,
}) => {
  return (
    <section
      className="w-full mt-6 sm:mt-7 select-none"
      id="orca-safety-map-section"
      aria-label="Area Safety Map"
    >
      {/* Section Header */}
      <div className="w-full flex items-center justify-between mb-2.5 px-1">
        <div>
          <h3 className="font-ui font-bold text-[18px] min-[390px]:text-[19px] sm:text-[20px] text-[#062A43] tracking-tight">
            {title}
          </h3>
          <p className="font-ui text-[12.5px] min-[390px]:text-[13px] text-[#567389] mt-0.5">
            {subtext}
          </p>
        </div>

        {/* View full map link */}
        <button
          type="button"
          onClick={onViewFullMap}
          className="inline-flex items-center gap-1 text-[12.5px] min-[390px]:text-[13px] font-semibold text-[#1677A8] hover:text-[#062A43] transition-colors cursor-pointer shrink-0 pl-2 focus:outline-hidden"
        >
          <span>{viewFullMapText}</span>
        </button>
      </div>

      {/* 
        Compact Map Card:
        - Non-GIS, visually immediate comprehension
        - Shows coastline, Digha harbor pin, and 3 concentric safe/caution/danger zones
      */}
      <div className="relative w-full h-[220px] min-[390px]:h-[235px] sm:h-[250px] rounded-[22px] overflow-hidden bg-[#D8EBF7] border border-[#BBD9EE] shadow-[0_4px_20px_rgba(6,42,67,0.06)] flex flex-col justify-between p-3.5 sm:p-4">
        {/* SVG Coastal Vector Map & Risk Zones */}
        <svg
          className="absolute inset-0 w-full h-full object-cover pointer-events-none"
          viewBox="0 0 400 240"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            {/* Soft water gradient */}
            <linearGradient id="seaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#C9E6F8" />
              <stop offset="60%" stopColor="#A8D5F2" />
              <stop offset="100%" stopColor="#81BEE5" />
            </linearGradient>

            {/* Land Coast gradient (West Bengal / Odisha coast) */}
            <linearGradient id="landGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#E5EFE6" />
              <stop offset="100%" stopColor="#D2E4D5" />
            </linearGradient>

            {/* Wave pattern */}
            <pattern id="wavesGrid" width="40" height="20" patternUnits="userSpaceOnUse">
              <path
                d="M0 10 Q10 5, 20 10 T40 10"
                fill="none"
                stroke="rgba(255,255,255,0.35)"
                strokeWidth="1.2"
              />
            </pattern>
          </defs>

          {/* Background: Open Sea (Bay of Bengal) */}
          <rect width="400" height="240" fill="url(#seaGrad)" />
          <rect width="400" height="240" fill="url(#wavesGrid)" />

          {/* Concentric Sea Risk Zones radiating from Digha Coast (x:130, y:65) */}

          {/* 1. Danger Zone (>30 km offshore in open shelf) */}
          <ellipse
            cx="140"
            cy="70"
            rx="270"
            ry="170"
            fill="rgba(239, 68, 68, 0.16)"
            stroke="rgba(220, 38, 38, 0.45)"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />

          {/* 2. Caution Zone (15–30 km offshore) */}
          <ellipse
            cx="140"
            cy="70"
            rx="190"
            ry="115"
            fill="rgba(245, 158, 11, 0.22)"
            stroke="rgba(217, 119, 6, 0.55)"
            strokeWidth="1.8"
          />

          {/* 3. Green Safe Zone (0–15 km nearshore sheltered waters) */}
          <ellipse
            cx="140"
            cy="70"
            rx="110"
            ry="68"
            fill="rgba(16, 185, 129, 0.32)"
            stroke="rgba(5, 150, 105, 0.75)"
            strokeWidth="2.2"
          />

          {/* Coastline Polygon (West Bengal coastline winding from top-left to right) */}
          <path
            d="M -10 -10 L 410 -10 L 410 40 Q 320 45, 250 55 T 140 68 T 50 95 L -10 130 Z"
            fill="url(#landGrad)"
            stroke="#A3C7AA"
            strokeWidth="2.5"
          />

          {/* Sand Beach Line */}
          <path
            d="M -10 130 L 50 95 Q 100 80, 140 68 T 250 55 Q 320 45, 410 40"
            fill="none"
            stroke="#E3C49B"
            strokeWidth="3.5"
          />

          {/* Zone Radius Labels in Sea */}
          <text x="210" y="115" fill="#047857" fontSize="9" fontWeight="700" fontFamily="DM Sans">
            15 km SAFE
          </text>
          <text x="280" y="150" fill="#B45309" fontSize="9" fontWeight="700" fontFamily="DM Sans">
            30 km CAUTION
          </text>
          <text x="320" y="210" fill="#B91C1C" fontSize="9" fontWeight="700" fontFamily="DM Sans">
            DEEP SEA
          </text>
        </svg>

        {/* Top Overlay: Compass Rose & Coastal Label */}
        <div className="relative z-10 w-full flex items-start justify-between">
          <div className="bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded-lg border border-[#D8E6F0] shadow-2xs">
            <span className="font-ui text-[11px] font-bold text-[#062A43] tracking-wide uppercase">
              West Bengal Coast
            </span>
          </div>

          <div className="w-7 h-7 rounded-full bg-white/90 backdrop-blur-xs border border-[#D8E6F0] flex items-center justify-center shadow-2xs">
            <Compass size={16} className="text-[#1677A8]" />
          </div>
        </div>

        {/* Harbor Pin (Digha) */}
        <div
          className="absolute left-[34%] top-[26%] z-10 flex flex-col items-center"
          style={{ transform: 'translate(-50%, -50%)' }}
        >
          <div className="px-2 py-0.5 rounded-md bg-[#062A43] text-white text-[10px] font-bold shadow-md whitespace-nowrap mb-1 flex items-center gap-1">
            <MapPin size={10} className="text-[#38BDF8]" />
            <span>Digha Harbour</span>
          </div>
          <div className="w-3.5 h-3.5 rounded-full bg-[#1677A8] border-2 border-white shadow-sm flex items-center justify-center animate-pulse">
            <div className="w-1.5 h-1.5 rounded-full bg-white" />
          </div>
        </div>

        {/* Bottom Bar: Clear risk zones legend */}
        <div className="relative z-10 w-full bg-white/95 backdrop-blur-md rounded-xl p-2 sm:p-2.5 border border-[#D8E6F0] shadow-xs flex items-center justify-between flex-wrap gap-1.5">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] shrink-0" />
            <span className="font-ui text-[10.5px] min-[390px]:text-[11px] font-semibold text-[#166534]">
              {safeLegend}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B] shrink-0" />
            <span className="font-ui text-[10.5px] min-[390px]:text-[11px] font-semibold text-[#92400E]">
              {cautionLegend}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] shrink-0" />
            <span className="font-ui text-[10.5px] min-[390px]:text-[11px] font-semibold text-[#991B1B]">
              {dangerLegend}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

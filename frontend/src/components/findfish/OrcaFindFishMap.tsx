import React, { useState } from 'react';
import { Plus, Minus, Navigation, Crosshair, AlertTriangle } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';

interface OrcaFindFishMapProps {
  translations: FindFishTranslations;
  selectedZoneId?: string;
  onSelectZone?: (zoneId: string) => void;
  onGoToBest?: () => void;
}

export const OrcaFindFishMap: React.FC<OrcaFindFishMapProps> = ({
  translations,
  selectedZoneId = 'best-spot',
  onSelectZone,
  onGoToBest,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [activeTabZone, setActiveTabZone] = useState<string>(selectedZoneId);

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 1.75));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.25, 0.75));
  };

  const handleResetLocation = () => {
    setZoomLevel(1);
    setActiveTabZone('best-spot');
    onSelectZone?.('best-spot');
  };

  const handleZoneClick = (zoneId: string) => {
    setActiveTabZone(zoneId);
    onSelectZone?.(zoneId);
  };

  return (
    <section
      className="relative w-full rounded-2xl sm:rounded-3xl overflow-hidden border border-[#BCD4E4] bg-[#EAF4FB] shadow-md transition-all select-none"
      id="orca-main-fishing-map-card"
      aria-label="Interactive Marine Fishing Zone Map"
    >
      {/* 
        MAP CANVAS CONTAINER:
        Realistic coastal navigation chart rendering with responsive SVG
      */}
      <div className="relative w-full h-[320px] min-[390px]:h-[360px] sm:h-[400px] md:h-[440px] overflow-hidden bg-gradient-to-br from-[#DCEFF9] via-[#CEE6F5] to-[#BFDDF0]">
        <div
          className="w-full h-full transition-transform duration-300 ease-out origin-center flex items-center justify-center"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <svg
            viewBox="0 0 500 400"
            className="w-full h-full object-cover"
            preserveAspectRatio="xMidYMid slice"
            role="img"
            aria-label="Map showing Digha coast, best fishing spot, good fishing area, and avoid area"
          >
            <defs>
              {/* Radial gradient for coastal depth */}
              <radialGradient id="oceanShallow" cx="30%" cy="20%" r="90%">
                <stop offset="0%" stopColor="#E2F2FB" />
                <stop offset="50%" stopColor="#CFE7F6" />
                <stop offset="100%" stopColor="#B3DAEF" />
              </radialGradient>

              {/* Best zone (Green) glow */}
              <radialGradient id="greenZoneGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#22C55E" stopOpacity="0.45" />
                <stop offset="70%" stopColor="#16A34A" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#15803D" stopOpacity="0" />
              </radialGradient>

              {/* Good zone (Yellow) glow */}
              <radialGradient id="yellowZoneGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#EAB308" stopOpacity="0.4" />
                <stop offset="70%" stopColor="#CA8A04" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#A16207" stopOpacity="0" />
              </radialGradient>

              {/* Avoid zone (Red) glow */}
              <radialGradient id="redZoneGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#EF4444" stopOpacity="0.4" />
                <stop offset="70%" stopColor="#DC2626" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#B91C1C" stopOpacity="0" />
              </radialGradient>

              {/* Diagonal hatch for avoid zone */}
              <pattern
                id="avoidHatch"
                width="8"
                height="8"
                patternTransform="rotate(45 0 0)"
                patternUnits="userSpaceOnUse"
              >
                <line x1="0" y1="0" x2="0" y2="8" stroke="#EF4444" strokeWidth="1.5" strokeOpacity="0.5" />
              </pattern>
            </defs>

            {/* Base Sea Background */}
            <rect width="500" height="400" fill="url(#oceanShallow)" />

            {/* Bathymetric Depth Contours */}
            {/* 10m depth isobath */}
            <path
              d="M -10 170 Q 140 180 250 140 T 510 110"
              fill="none"
              stroke="#A2CEE8"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            <text x="440" y="105" fill="#5F97BA" fontSize="9" fontWeight="600" fontFamily="DM Sans, sans-serif">
              10m depth
            </text>

            {/* 20m depth isobath */}
            <path
              d="M -10 260 Q 150 270 300 220 T 510 190"
              fill="none"
              stroke="#8DBFD9"
              strokeWidth="1.5"
              strokeDasharray="5 5"
            />
            <text x="440" y="185" fill="#5F97BA" fontSize="9" fontWeight="600" fontFamily="DM Sans, sans-serif">
              20m depth
            </text>

            {/* 30m depth isobath */}
            <path
              d="M -10 340 Q 180 350 360 300 T 510 270"
              fill="none"
              stroke="#7EAFC9"
              strokeWidth="1.5"
              strokeDasharray="6 6"
            />
            <text x="440" y="265" fill="#4B89AF" fontSize="9" fontWeight="600" fontFamily="DM Sans, sans-serif">
              30m depth
            </text>

            {/* Coastal Landmass (North-West / Top-Left) */}
            <path
              d="M -20 -20 
                 L 260 -20 
                 Q 230 45 190 75 
                 Q 140 105 100 125 
                 Q 50 145 -20 155 
                 Z"
              fill="#E5EDE0"
              stroke="#CBD9C3"
              strokeWidth="2"
            />

            {/* Sandy Shoreline Strip */}
            <path
              d="M -20 155 
                 Q 50 145 100 125 
                 Q 140 105 190 75 
                 Q 230 45 260 -20"
              fill="none"
              stroke="#D8C7A3"
              strokeWidth="5"
              strokeLinecap="round"
            />

            {/* Land Area Labels */}
            <g transform="translate(45, 45)">
              <text fill="#4A6546" fontSize="13" fontWeight="700" fontFamily="DM Sans, sans-serif" letterSpacing="0.05em">
                WEST BENGAL
              </text>
              <text x="0" y="18" fill="#688463" fontSize="11" fontWeight="500" fontFamily="DM Sans, sans-serif">
                Coastal District
              </text>
            </g>

            {/* ---------------------------------------------------- */}
            {/* DISTANCE RINGS FROM DIGHA HARBOUR (10km, 20km, 30km) */}
            {/* ---------------------------------------------------- */}
            {/* Harbour origin at (90, 130) */}
            <circle cx="90" cy="130" r="100" fill="none" stroke="#2563EB" strokeWidth="0.8" strokeOpacity="0.25" strokeDasharray="3 3" />
            <text x="145" y="222" fill="#1D4ED8" fontSize="8.5" fontWeight="600" opacity="0.6">10 km</text>

            <circle cx="90" cy="130" r="180" fill="none" stroke="#2563EB" strokeWidth="0.8" strokeOpacity="0.2" strokeDasharray="3 3" />
            <text x="215" y="285" fill="#1D4ED8" fontSize="8.5" fontWeight="600" opacity="0.6">20 km</text>

            {/* Navigation Course Vector (Digha -> Best Spot) */}
            <line
              x1="90"
              y1="130"
              x2="225"
              y2="230"
              stroke="#15803D"
              strokeWidth="2.5"
              strokeDasharray="6 4"
            />
            {/* Bearing label */}
            <rect x="145" y="165" width="48" height="18" rx="9" fill="#FFFFFF" fillOpacity="0.92" stroke="#15803D" strokeWidth="1" />
            <text x="169" y="177" textAnchor="middle" fill="#166534" fontSize="9.5" fontWeight="700" fontFamily="DM Sans, sans-serif">
              145° SE
            </text>

            {/* ---------------------------------------------------- */}
            {/* 3 FISHING ZONES ONLY: BEST (🟢), GOOD (🟡), AVOID (🔴) */}
            {/* ---------------------------------------------------- */}

            {/* 1. 🔴 AVOID ZONE (Shifting Sandbar / High Cross-Currents) */}
            <g
              className="cursor-pointer transition-transform hover:scale-105"
              onClick={() => handleZoneClick('avoid-zone')}
              role="button"
              tabIndex={0}
              aria-label="Avoid area: Submerged sandbar and rough shoals"
            >
              {/* Avoid Zone Boundary */}
              <ellipse cx="370" cy="90" rx="55" ry="35" fill="url(#redZoneGlow)" />
              <ellipse
                cx="370"
                cy="90"
                rx="50"
                ry="30"
                fill="url(#avoidHatch)"
                stroke="#DC2626"
                strokeWidth="2"
                strokeDasharray="5 3"
              />
              {/* Avoid Label Badge */}
              <g transform="translate(370, 90)">
                <rect x="-42" y="-14" width="84" height="28" rx="14" fill="#FEF2F2" stroke="#EF4444" strokeWidth="1.5" />
                <circle cx="-25" cy="0" r="7" fill="#EF4444" />
                <text x="-25" y="3.5" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="900">✕</text>
                <text x="3" y="4" textAnchor="middle" fill="#991B1B" fontSize="12" fontWeight="700" fontFamily="DM Sans, sans-serif">
                  {translations.mapAvoidZone}
                </text>
              </g>
            </g>

            {/* 2. 🟡 GOOD ZONE (18 km - 25 km Offshore Area) */}
            <g
              className="cursor-pointer transition-transform hover:scale-105"
              onClick={() => handleZoneClick('good-spot-1')}
              role="button"
              tabIndex={0}
              aria-label="Good spot: 18km to 25km offshore"
            >
              {/* Outer Amber Zone */}
              <ellipse cx="340" cy="275" rx="75" ry="45" fill="url(#yellowZoneGlow)" />
              <ellipse
                cx="340"
                cy="275"
                rx="70"
                ry="40"
                fill="#FEF08A"
                fillOpacity="0.25"
                stroke="#CA8A04"
                strokeWidth="2"
                strokeDasharray="4 4"
              />
              {/* Good Label Badge */}
              <g transform="translate(340, 275)">
                <rect x="-46" y="-14" width="92" height="28" rx="14" fill="#FEFCE8" stroke="#EAB308" strokeWidth="1.5" />
                <circle cx="-28" cy="0" r="7" fill="#EAB308" />
                <text x="-28" y="3" textAnchor="middle" fill="#FFFFFF" fontSize="8.5" fontWeight="900">✓</text>
                <text x="3" y="4" textAnchor="middle" fill="#854D0E" fontSize="12" fontWeight="700" fontFamily="DM Sans, sans-serif">
                  {translations.mapGoodZone}
                </text>
              </g>
            </g>

            {/* 3. 🟢 BEST FISHING ZONE (12 km Offshore - Focal Point) */}
            <g
              className="cursor-pointer transition-transform hover:scale-105"
              onClick={() => handleZoneClick('best-spot')}
              role="button"
              tabIndex={0}
              aria-label="Best spot: 12 km offshore, recommended by ORCA"
            >
              {/* Radiating Sonar Animation Ring for Best Spot */}
              <circle cx="225" cy="230" r="54" fill="url(#greenZoneGlow)">
                <animate attributeName="r" values="46;58;46" dur="3s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.7;0.3;0.7" dur="3s" repeatCount="indefinite" />
              </circle>

              <ellipse
                cx="225"
                cy="230"
                rx="48"
                ry="36"
                fill="#86EFAC"
                fillOpacity="0.3"
                stroke="#16A34A"
                strokeWidth="2.5"
              />

              {/* Fish school indicators inside green zone */}
              <g transform="translate(225, 208)">
                <circle cx="-14" cy="0" r="3" fill="#15803D" opacity="0.8" />
                <circle cx="0" cy="-3" r="3.5" fill="#16A34A" />
                <circle cx="12" cy="1" r="3" fill="#15803D" opacity="0.8" />
              </g>

              {/* Dominant Best Spot Badge */}
              <g transform="translate(225, 236)">
                <rect
                  x="-58"
                  y="-17"
                  width="116"
                  height="34"
                  rx="17"
                  fill="#15803D"
                  stroke="#FFFFFF"
                  strokeWidth="2"
                  filter="drop-shadow(0 2px 4px rgba(0,0,0,0.15))"
                />
                {/* Visual Icon: Fish/Hook */}
                <text x="-40" y="5" fontSize="14">🎣</text>
                {/* Text Label */}
                <text
                  x="-2"
                  y="4"
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize="13"
                  fontWeight="800"
                  fontFamily="DM Sans, sans-serif"
                  letterSpacing="0.02em"
                >
                  {translations.mapBestZone}
                </text>
              </g>

              {/* Distance Callout */}
              <g transform="translate(225, 270)">
                <rect x="-34" y="-10" width="68" height="20" rx="10" fill="#FFFFFF" fillOpacity="0.95" stroke="#16A34A" strokeWidth="1" />
                <text x="0" y="4" textAnchor="middle" fill="#166534" fontSize="11" fontWeight="700" fontFamily="DM Sans, sans-serif">
                  12 km
                </text>
              </g>
            </g>

            {/* ---------------------------------------------------- */}
            {/* CURRENT LOCATION PIN: DIGHA HARBOUR (STARTING POINT) */}
            {/* ---------------------------------------------------- */}
            <g transform="translate(90, 130)" className="cursor-pointer">
              {/* Radar pulse */}
              <circle cx="0" cy="0" r="14" fill="#0284C7" fillOpacity="0.25">
                <animate attributeName="r" values="10;20;10" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.6;0.1;0.6" dur="2s" repeatCount="indefinite" />
              </circle>

              {/* Harbor point */}
              <circle cx="0" cy="0" r="7" fill="#0284C7" stroke="#FFFFFF" strokeWidth="2.5" />
              <circle cx="0" cy="0" r="2.5" fill="#FFFFFF" />

              {/* Harbour Label Card */}
              <g transform="translate(0, -18)">
                <rect
                  x="-48"
                  y="-12"
                  width="96"
                  height="22"
                  rx="11"
                  fill="#062A43"
                  stroke="#FFFFFF"
                  strokeWidth="1.5"
                />
                <text
                  x="0"
                  y="3"
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize="10.5"
                  fontWeight="700"
                  fontFamily="DM Sans, sans-serif"
                >
                  📍 {translations.mapCurrentLocation}
                </text>
              </g>
            </g>

            {/* Compass Rose / North Indicator */}
            <g transform="translate(38, 355)">
              <circle cx="0" cy="0" r="16" fill="#FFFFFF" fillOpacity="0.9" stroke="#BACEDC" strokeWidth="1" />
              <path d="M 0 -12 L 4 0 L 0 3 L -4 0 Z" fill="#062A43" />
              <path d="M 0 12 L 4 0 L 0 -3 L -4 0 Z" fill="#A0AEC0" />
              <text x="0" y="-15" textAnchor="middle" fill="#062A43" fontSize="9" fontWeight="800">
                N
              </text>
            </g>

            {/* Distance Scale Bar */}
            <g transform="translate(85, 368)">
              <rect x="-4" y="-12" width="108" height="20" rx="4" fill="#FFFFFF" fillOpacity="0.9" stroke="#C5D7E4" strokeWidth="0.8" />
              <line x1="6" y1="-2" x2="94" y2="-2" stroke="#062A43" strokeWidth="2" />
              <line x1="6" y1="-5" x2="6" y2="1" stroke="#062A43" strokeWidth="2" />
              <line x1="50" y1="-4" x2="50" y2="0" stroke="#062A43" strokeWidth="1.5" />
              <line x1="94" y1="-5" x2="94" y2="1" stroke="#062A43" strokeWidth="2" />
              <text x="6" y="7" textAnchor="middle" fill="#062A43" fontSize="8" fontWeight="600">0</text>
              <text x="50" y="7" textAnchor="middle" fill="#062A43" fontSize="8" fontWeight="600">10 km</text>
              <text x="94" y="7" textAnchor="middle" fill="#062A43" fontSize="8" fontWeight="600">20 km</text>
            </g>
          </svg>
        </div>

        {/* 
          FLOATING MAP CONTROLS:
          - Zoom in (+)
          - Zoom out (−)
          - Center on current location
        */}
        <div className="absolute top-3 right-3 flex flex-col items-center gap-2 z-10">
          <div className="flex flex-col rounded-xl bg-white/95 backdrop-blur-md border border-[#C6DCED] shadow-sm overflow-hidden">
            <button
              type="button"
              onClick={handleZoomIn}
              aria-label="Zoom in on fishing map"
              className="w-10 h-10 min-[390px]:w-11 min-[390px]:h-11 flex items-center justify-center text-[#062A43] hover:bg-[#F0F7FC] active:bg-[#E2EFF8] transition-colors border-b border-[#E2EFF8] cursor-pointer"
            >
              <Plus size={18} strokeWidth={2.5} />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              aria-label="Zoom out on fishing map"
              className="w-10 h-10 min-[390px]:w-11 min-[390px]:h-11 flex items-center justify-center text-[#062A43] hover:bg-[#F0F7FC] active:bg-[#E2EFF8] transition-colors cursor-pointer"
            >
              <Minus size={18} strokeWidth={2.5} />
            </button>
          </div>

          {/* Reset / Center Location Button */}
          <button
            type="button"
            onClick={handleResetLocation}
            aria-label="Center map on Digha Harbour and best spot"
            className="w-10 h-10 min-[390px]:w-11 min-[390px]:h-11 rounded-xl bg-white/95 backdrop-blur-md border border-[#C6DCED] shadow-sm flex items-center justify-center text-[#1677A8] hover:bg-[#F0F7FC] active:scale-95 transition-all cursor-pointer"
          >
            <Crosshair size={19} strokeWidth={2.2} />
          </button>
        </div>
      </div>

      {/* 
        MAP BOTTOM LEGEND:
        Clear 3 colored zones for instant visual recognition:
        🟢 Best fishing | 🟡 Good | 🔴 Avoid
      */}
      <div
        className="w-full bg-white/95 border-t border-[#BCD4E4] px-4 py-3 flex flex-wrap items-center justify-between gap-2.5"
        role="region"
        aria-label="Map Zone Legend"
      >
        <div className="flex items-center flex-wrap gap-3 sm:gap-4 text-[12.5px] min-[390px]:text-[13.5px] font-semibold text-[#062A43]">
          {/* Green Zone */}
          <div
            onClick={() => handleZoneClick('best-spot')}
            className={`flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded-lg transition-colors ${
              activeTabZone === 'best-spot' ? 'bg-[#EBF7EE] text-[#166534]' : 'hover:bg-black/5'
            }`}
          >
            <span className="w-3.5 h-3.5 rounded-full bg-[#22C55E] border-2 border-white shadow-xs shrink-0" />
            <span className="font-ui">{translations.mapBestZone}</span>
          </div>

          {/* Yellow Zone */}
          <div
            onClick={() => handleZoneClick('good-spot-1')}
            className={`flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded-lg transition-colors ${
              activeTabZone === 'good-spot-1' || activeTabZone === 'good-spot-2' ? 'bg-[#FEFCE8] text-[#854D0E]' : 'hover:bg-black/5'
            }`}
          >
            <span className="w-3.5 h-3.5 rounded-full bg-[#EAB308] border-2 border-white shadow-xs shrink-0" />
            <span className="font-ui">{translations.mapGoodZone}</span>
          </div>

          {/* Red Zone */}
          <div
            onClick={() => handleZoneClick('avoid-zone')}
            className={`flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded-lg transition-colors ${
              activeTabZone === 'avoid-zone' ? 'bg-[#FEF2F2] text-[#991B1B]' : 'hover:bg-black/5'
            }`}
          >
            <span className="w-3.5 h-3.5 rounded-full bg-[#EF4444] border-2 border-white shadow-xs shrink-0" />
            <span className="font-ui">{translations.mapAvoidZone}</span>
          </div>
        </div>

        {/* Quick action button to focus recommendation */}
        {onGoToBest && (
          <button
            type="button"
            onClick={onGoToBest}
            className="text-[12.5px] font-semibold text-[#1677A8] hover:text-[#0D5B84] flex items-center gap-1 cursor-pointer ml-auto"
          >
            <span>{translations.bestDistance}</span>
            <Navigation size={13} className="rotate-45" />
          </button>
        )}
      </div>
    </section>
  );
};

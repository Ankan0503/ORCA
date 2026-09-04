import React, { useState, useRef, useEffect, useId } from 'react';
import { MapZone, MapTranslations, MAP_ZONES_CONFIG } from '../../data/mapData';
import { MapFilterType } from './OrcaMapFilterBar';

interface OrcaMarineMapCanvasProps {
  activeFilter: MapFilterType;
  showRoute: boolean;
  onSelectZone: (zone: MapZone) => void;
  selectedZoneId?: string;
  zoomLevel: number;
  panOffset: { x: number; y: number };
  onPanChange: (pan: { x: number; y: number }) => void;
  translations: MapTranslations;
}

export const OrcaMarineMapCanvas: React.FC<OrcaMarineMapCanvasProps> = ({
  activeFilter,
  showRoute,
  onSelectZone,
  selectedZoneId,
  zoomLevel,
  panOffset,
  onPanChange,
  translations,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const basePanRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Touch and mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    basePanRef.current = { ...panOffset };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    onPanChange({
      x: basePanRef.current.x + dx,
      y: basePanRef.current.y + dy,
    });
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      isDraggingRef.current = true;
      dragStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      basePanRef.current = { ...panOffset };
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDraggingRef.current || e.touches.length !== 1) return;
    const dx = e.touches[0].clientX - dragStartRef.current.x;
    const dy = e.touches[0].clientY - dragStartRef.current.y;
    onPanChange({
      x: basePanRef.current.x + dx,
      y: basePanRef.current.y + dy,
    });
  };

  const handleTouchEnd = () => {
    isDraggingRef.current = false;
  };

  const bestZone = MAP_ZONES_CONFIG.find((z) => z.id === 'best-zone')!;
  const goodZone = MAP_ZONES_CONFIG.find((z) => z.id === 'good-zone')!;
  const avoidZone = MAP_ZONES_CONFIG.find((z) => z.id === 'avoid-zone')!;
  const restrictedZone = MAP_ZONES_CONFIG.find((z) => z.id === 'restricted-zone')!;

  // Harbor origin (Digha)
  const harborX = 110;
  const harborY = 175;

  // Best Spot center
  const bestX = 265;
  const bestY = 370;

  // Good Spot center
  const goodX = 405;
  const goodY = 475;

  // Avoid Spot center (Storm / Shoals)
  const avoidX = 425;
  const avoidY = 180;

  // Restricted Spot center (Sanctuary / Fairway)
  const restX = 135;
  const restY = 490;

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      id="orca-marine-map-canvas-container"
      className="relative w-full h-full min-h-[100svh] min-h-[100dvh] overflow-hidden bg-gradient-to-b from-[#D4ECF9] via-[#C5E4F5] to-[#B0D9EE] cursor-grab active:cursor-grabbing select-none"
    >
      {/* Scalable & Pannable SVG World */}
      <div
        className="w-full h-full transition-transform duration-100 ease-out origin-center flex items-center justify-center pointer-events-auto"
        style={{
          transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
        }}
      >
        <svg
          viewBox="0 0 540 680"
          className="w-full h-full min-w-[540px] min-h-[680px] object-cover"
          preserveAspectRatio="xMidYMid slice"
          role="img"
          aria-label="Marine map showing Digha, best fishing area, good fishing area, avoid area, and restricted area"
        >
          <defs>
            {/* Ocean gradients */}
            <radialGradient id="oceanBg" cx="40%" cy="40%" r="80%">
              <stop offset="0%" stopColor="#E2F2FC" />
              <stop offset="45%" stopColor="#C9E6F8" />
              <stop offset="100%" stopColor="#A8D4EE" />
            </radialGradient>

            {/* Best zone (Green) glow */}
            <radialGradient id="greenGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#22C55E" stopOpacity="0.5" />
              <stop offset="70%" stopColor="#16A34A" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#15803D" stopOpacity="0" />
            </radialGradient>

            {/* Good zone (Yellow) glow */}
            <radialGradient id="yellowGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#EAB308" stopOpacity="0.45" />
              <stop offset="70%" stopColor="#CA8A04" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#A16207" stopOpacity="0" />
            </radialGradient>

            {/* Avoid zone (Red) glow */}
            <radialGradient id="redGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#EF4444" stopOpacity="0.45" />
              <stop offset="70%" stopColor="#DC2626" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#B91C1C" stopOpacity="0" />
            </radialGradient>

            {/* Avoid diagonal hatch */}
            <pattern
              id="mapAvoidHatch"
              width="10"
              height="10"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="10" stroke="#EF4444" strokeWidth="2" strokeOpacity="0.4" />
            </pattern>

            {/* Restricted area subtle stripes pattern */}
            <pattern
              id="restrictedStripe"
              width="12"
              height="12"
              patternTransform="rotate(-45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="12" stroke="#64748B" strokeWidth="2" strokeOpacity="0.45" />
              <line x1="6" y1="0" x2="6" y2="12" stroke="#94A3B8" strokeWidth="1" strokeOpacity="0.3" />
            </pattern>

            {/* PFZ Frontal Glow */}
            <radialGradient id="pfzGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.4" />
              <stop offset="60%" stopColor="#0284C7" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#0369A1" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Base Ocean Background */}
          <rect width="540" height="680" fill="url(#oceanBg)" />

          {/* Bathymetric Depth Contours */}
          <g opacity="0.65">
            {/* 5m contour */}
            <path
              d="M -20 220 Q 120 225 210 180 T 560 130"
              fill="none"
              stroke="#A0D0EC"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            <text x="480" y="125" fill="#4B89AF" fontSize="9" fontWeight="700" fontFamily="DM Sans, sans-serif">
              5m depth
            </text>

            {/* 10m contour */}
            <path
              d="M -20 320 Q 150 330 290 270 T 560 220"
              fill="none"
              stroke="#8EC5E6"
              strokeWidth="1.5"
              strokeDasharray="5 5"
            />
            <text x="480" y="215" fill="#3B7DAB" fontSize="9" fontWeight="700" fontFamily="DM Sans, sans-serif">
              10m depth
            </text>

            {/* 20m contour */}
            <path
              d="M -20 450 Q 180 470 360 410 T 560 360"
              fill="none"
              stroke="#7AB7DD"
              strokeWidth="1.5"
              strokeDasharray="6 6"
            />
            <text x="480" y="355" fill="#2E6F9E" fontSize="9" fontWeight="700" fontFamily="DM Sans, sans-serif">
              20m depth
            </text>

            {/* 30m contour */}
            <path
              d="M -20 580 Q 210 600 410 540 T 560 490"
              fill="none"
              stroke="#68A9D4"
              strokeWidth="1.5"
              strokeDasharray="6 6"
            />
            <text x="480" y="485" fill="#24608E" fontSize="9" fontWeight="700" fontFamily="DM Sans, sans-serif">
              30m depth
            </text>
          </g>

          {/* Coastal Landmass (North-West / Top-Left of Digha) */}
          <path
            d="M -20 -20 
               L 310 -20 
               Q 270 55 220 95 
               Q 160 140 110 175 
               Q 60 200 -20 215 
               Z"
            fill="#E4ECE0"
            stroke="#CBD8C3"
            strokeWidth="2.5"
          />

          {/* Sandy Shoreline Strip */}
          <path
            d="M -20 215 
               Q 60 200 110 175 
               Q 160 140 220 95 
               Q 270 55 310 -20"
            fill="none"
            stroke="#DECBA3"
            strokeWidth="6"
            strokeLinecap="round"
          />

          {/* Land Area Labels */}
          <g transform="translate(45, 55)">
            <text fill="#3D5A39" fontSize="14" fontWeight="800" fontFamily="DM Sans, sans-serif" letterSpacing="0.06em">
              WEST BENGAL
            </text>
            <text x="0" y="20" fill="#5F7E5B" fontSize="11.5" fontWeight="600" fontFamily="DM Sans, sans-serif">
              Purba Medinipur Coast
            </text>
            <text x="0" y="36" fill="#7A9A76" fontSize="10.5" fontWeight="500" fontFamily="DM Sans, sans-serif">
              Digha • Shankarpur
            </text>
          </g>

          {/* Distance Reference Rings from Digha Harbour (10 km & 20 km) */}
          <circle
            cx={harborX}
            cy={harborY}
            r="120"
            fill="none"
            stroke="#0284C7"
            strokeWidth="1"
            strokeOpacity="0.3"
            strokeDasharray="4 4"
          />
          <text x="180" y="290" fill="#0369A1" fontSize="9.5" fontWeight="700" opacity="0.65">
            10 km
          </text>

          <circle
            cx={harborX}
            cy={harborY}
            r="220"
            fill="none"
            stroke="#0284C7"
            strokeWidth="1"
            strokeOpacity="0.25"
            strokeDasharray="4 4"
          />
          <text x="260" y="385" fill="#0369A1" fontSize="9.5" fontWeight="700" opacity="0.65">
            20 km
          </text>

          {/* 
            PFZ Satellite Layer (Highlighted when activeFilter === 'pfz')
          */}
          {activeFilter === 'pfz' && (
            <g opacity="0.8" className="animate-fade-in">
              <ellipse cx={bestX} cy={bestY} rx="75" ry="55" fill="url(#pfzGlow)" />
              <path
                d="M 200 340 Q 280 330 360 440"
                fill="none"
                stroke="#06B6D4"
                strokeWidth="3.5"
                strokeDasharray="6 3"
                opacity="0.85"
              />
              <g transform="translate(290, 325)">
                <rect x="-42" y="-12" width="84" height="24" rx="12" fill="#ECFEFF" stroke="#06B6D4" strokeWidth="1.5" />
                <text x="0" y="4" textAnchor="middle" fill="#0E7490" fontSize="10.5" fontWeight="800" fontFamily="DM Sans, sans-serif">
                  PFZ FRONTAL ZONE
                </text>
              </g>
            </g>
          )}

          {/* 
            ===================================================================
            ZONE 1: 🔴 AVOID AREA (Storm-Risk Zone / Sandbar / Heavy Cross-Swells)
            ===================================================================
          */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => onSelectZone(avoidZone)}
            role="button"
            tabIndex={0}
            aria-label="Avoid area: Storm risk zone"
          >
            {/* Avoid Zone Outer Glow */}
            <ellipse cx={avoidX} cy={avoidY} rx="65" ry="42" fill="url(#redGlow)" />
            {/* Avoid Hatch Pattern Fill */}
            <ellipse
              cx={avoidX}
              cy={avoidY}
              rx="60"
              ry="38"
              fill="url(#mapAvoidHatch)"
              stroke="#DC2626"
              strokeWidth="2.5"
              strokeDasharray="6 4"
            />
            {/* Dominant Label Badge */}
            <g transform={`translate(${avoidX}, ${avoidY})`}>
              <rect
                x="-58"
                y="-17"
                width="116"
                height="34"
                rx="17"
                fill="#FEF2F2"
                stroke="#DC2626"
                strokeWidth="2"
                filter="drop-shadow(0 2px 4px rgba(220,38,38,0.15))"
              />
              <circle cx="-38" cy="0" r="9" fill="#DC2626" />
              <text x="-38" y="4" textAnchor="middle" fill="#FFFFFF" fontSize="11" fontWeight="900">
                ✕
              </text>
              <text
                x="8"
                y="4.5"
                textAnchor="middle"
                fill="#991B1B"
                fontSize="12.5"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
              >
                {translations.legend.avoid}
              </text>
            </g>
            {/* Warning Sub-Badge */}
            <g transform={`translate(${avoidX}, ${avoidY + 30})`}>
              <rect x="-42" y="-9" width="84" height="18" rx="9" fill="#FFFFFF" fillOpacity="0.95" stroke="#EF4444" strokeWidth="1" />
              <text x="0" y="3.5" textAnchor="middle" fill="#B91C1C" fontSize="9.5" fontWeight="700" fontFamily="DM Sans, sans-serif">
                Storm risk
              </text>
            </g>
          </g>

          {/* 
            ===================================================================
            ZONE 2: ⚪ RESTRICTED AREA (Protected Marine Sanctuary & Shipping Fairway)
            - Visually obvious subtle striped / outlined red/gray area
            - Clearly labeled "Restricted area"
            - Tap shows "Restricted area: Fishing is not allowed here."
            ===================================================================
          */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => onSelectZone(restrictedZone)}
            role="button"
            tabIndex={0}
            aria-label="Restricted area: Fishing is not allowed here"
          >
            {/* Outer boundary buffer */}
            <ellipse
              cx={restX}
              cy={restY}
              rx="56"
              ry="40"
              fill="#F1F5F9"
              fillOpacity="0.5"
            />
            {/* Striped interior pattern */}
            <ellipse
              cx={restX}
              cy={restY}
              rx="52"
              ry="36"
              fill="url(#restrictedStripe)"
              stroke="#64748B"
              strokeWidth="2.5"
              strokeDasharray="6 3"
            />
            {/* Red perimeter accent line */}
            <ellipse
              cx={restX}
              cy={restY}
              rx="46"
              ry="30"
              fill="none"
              stroke="#EF4444"
              strokeWidth="1.5"
              strokeDasharray="3 3"
              strokeOpacity="0.7"
            />
            {/* Labeled Badge */}
            <g transform={`translate(${restX}, ${restY})`}>
              <rect
                x="-64"
                y="-17"
                width="128"
                height="34"
                rx="17"
                fill="#FFFFFF"
                stroke="#64748B"
                strokeWidth="2"
                filter="drop-shadow(0 2px 4px rgba(0,0,0,0.12))"
              />
              {/* Prohibited icon */}
              <text x="-44" y="5" fontSize="13">
                🚫
              </text>
              <text
                x="4"
                y="4.5"
                textAnchor="middle"
                fill="#334155"
                fontSize="12"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
              >
                {translations.legend.restricted}
              </text>
            </g>
            {/* Clarification Sub-Pill */}
            <g transform={`translate(${restX}, ${restY + 30})`}>
              <rect x="-50" y="-9" width="100" height="18" rx="9" fill="#F8FAFC" stroke="#94A3B8" strokeWidth="1" />
              <text x="0" y="3.5" textAnchor="middle" fill="#475569" fontSize="9" fontWeight="700" fontFamily="DM Sans, sans-serif">
                No fishing zone
              </text>
            </g>
          </g>

          {/* 
            ===================================================================
            ZONE 3: 🟡 GOOD FISHING AREA (18 km Offshore)
            ===================================================================
          */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => onSelectZone(goodZone)}
            role="button"
            tabIndex={0}
            aria-label="Good fishing area: 18 km offshore"
          >
            {/* Amber Glow */}
            <ellipse cx={goodX} cy={goodY} rx="78" ry="48" fill="url(#yellowGlow)" />
            {/* Good Zone Boundary */}
            <ellipse
              cx={goodX}
              cy={goodY}
              rx="72"
              ry="44"
              fill="#FEF08A"
              fillOpacity="0.3"
              stroke="#CA8A04"
              strokeWidth="2"
              strokeDasharray="5 4"
            />
            {/* Label Badge */}
            <g transform={`translate(${goodX}, ${goodY})`}>
              <rect
                x="-58"
                y="-16"
                width="116"
                height="32"
                rx="16"
                fill="#FEFCE8"
                stroke="#EAB308"
                strokeWidth="2"
                filter="drop-shadow(0 2px 4px rgba(234,179,8,0.15))"
              />
              <circle cx="-38" cy="0" r="8" fill="#EAB308" />
              <text x="-38" y="3.5" textAnchor="middle" fill="#FFFFFF" fontSize="10" fontWeight="900">
                ✓
              </text>
              <text
                x="6"
                y="4"
                textAnchor="middle"
                fill="#854D0E"
                fontSize="12"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
              >
                {translations.legend.good}
              </text>
            </g>
            {/* Distance Sub-Pill */}
            <g transform={`translate(${goodX}, ${goodY + 28})`}>
              <rect x="-38" y="-9" width="76" height="18" rx="9" fill="#FFFFFF" fillOpacity="0.95" stroke="#EAB308" strokeWidth="1" />
              <text x="0" y="3.5" textAnchor="middle" fill="#854D0E" fontSize="9.5" fontWeight="700" fontFamily="DM Sans, sans-serif">
                18 km offshore
              </text>
            </g>
          </g>

          {/* 
            ===================================================================
            ROUTE: SIMPLE NAUTICAL ROUTE LINE (Your location -> Best Fishing Area)
            - Direct, high-contrast dashed line
            - Clear "12 km" distance indicator
            ===================================================================
          */}
          {showRoute && (
            <g className="animate-fade-in pointer-events-none">
              {/* Route glow line */}
              <line
                x1={harborX}
                y1={harborY}
                x2={bestX}
                y2={bestY}
                stroke="#22C55E"
                strokeWidth="6"
                strokeOpacity="0.3"
                strokeLinecap="round"
              />
              {/* Main Course Vector */}
              <line
                x1={harborX}
                y1={harborY}
                x2={bestX}
                y2={bestY}
                stroke="#15803D"
                strokeWidth="3"
                strokeDasharray="8 5"
                strokeLinecap="round"
              />
              {/* Route Midway Distance Badge: "12 km" */}
              <g transform={`translate(${(harborX + bestX) / 2}, ${(harborY + bestY) / 2})`}>
                <rect
                  x="-32"
                  y="-12"
                  width="64"
                  height="24"
                  rx="12"
                  fill="#062A43"
                  stroke="#FFFFFF"
                  strokeWidth="2"
                  filter="drop-shadow(0 2px 6px rgba(0,0,0,0.25))"
                />
                <text
                  x="0"
                  y="4"
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize="11"
                  fontWeight="800"
                  fontFamily="DM Sans, sans-serif"
                >
                  12 km
                </text>
              </g>
            </g>
          )}

          {/* 
            ===================================================================
            ZONE 4: 🟢 BEST FISHING AREA (12 km Offshore - Focal Point)
            - Green zone with radiating sonar pulse
            - Dominant high-contrast badge
            - Clear text: "Best fishing area" & "12 km offshore"
            ===================================================================
          */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => onSelectZone(bestZone)}
            role="button"
            tabIndex={0}
            aria-label="Best fishing area: 12 km offshore, safe to go"
          >
            {/* Animated Sonar Pulse Ring */}
            <circle cx={bestX} cy={bestY} r="58" fill="url(#greenGlow)">
              <animate attributeName="r" values="48;68;48" dur="2.8s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.8;0.2;0.8" dur="2.8s" repeatCount="indefinite" />
            </circle>

            {/* Inner green zone ellipse */}
            <ellipse
              cx={bestX}
              cy={bestY}
              rx="54"
              ry="40"
              fill="#86EFAC"
              fillOpacity="0.4"
              stroke="#16A34A"
              strokeWidth="3"
            />

            {/* Fish school indicators inside green area */}
            <g transform={`translate(${bestX}, ${bestY - 26})`}>
              <circle cx="-16" cy="0" r="3.5" fill="#15803D" />
              <circle cx="0" cy="-3" r="4" fill="#16A34A" />
              <circle cx="16" cy="1" r="3.5" fill="#15803D" />
            </g>

            {/* Dominant Green Spot Badge */}
            <g transform={`translate(${bestX}, ${bestY + 4})`}>
              <rect
                x="-68"
                y="-18"
                width="136"
                height="36"
                rx="18"
                fill="#15803D"
                stroke="#FFFFFF"
                strokeWidth="2.5"
                filter="drop-shadow(0 3px 8px rgba(21,128,61,0.3))"
              />
              <text x="-48" y="5" fontSize="15">
                🎣
              </text>
              <text
                x="6"
                y="5"
                textAnchor="middle"
                fill="#FFFFFF"
                fontSize="13"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
                letterSpacing="0.02em"
              >
                {translations.legend.best}
              </text>
            </g>

            {/* Distance Callout */}
            <g transform={`translate(${bestX}, ${bestY + 38})`}>
              <rect
                x="-42"
                y="-10"
                width="84"
                height="20"
                rx="10"
                fill="#FFFFFF"
                fillOpacity="0.95"
                stroke="#16A34A"
                strokeWidth="1.5"
                filter="drop-shadow(0 1px 3px rgba(0,0,0,0.1))"
              />
              <text
                x="0"
                y="4"
                textAnchor="middle"
                fill="#15803D"
                fontSize="10.5"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
              >
                12 km offshore
              </text>
            </g>
          </g>

          {/* 
            ===================================================================
            CURRENT LOCATION PIN: 🔵 DIGHA COAST / HARBOUR
            - Clear label: "📍 You are here"
            - Pulsing blue GPS radar dot
            ===================================================================
          */}
          <g
            transform={`translate(${harborX}, ${harborY})`}
            className="cursor-pointer"
            role="button"
            tabIndex={0}
            aria-label="You are here: Digha coast"
          >
            {/* Radar wave 1 */}
            <circle cx="0" cy="0" r="16" fill="#0284C7" fillOpacity="0.25">
              <animate attributeName="r" values="10;26;10" dur="2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.7;0.1;0.7" dur="2s" repeatCount="indefinite" />
            </circle>

            {/* Solid Navy/Blue Pin */}
            <circle cx="0" cy="0" r="9" fill="#0284C7" stroke="#FFFFFF" strokeWidth="2.5" />
            <circle cx="0" cy="0" r="3.5" fill="#FFFFFF" />

            {/* "You are here" Floating Card */}
            <g transform="translate(0, -22)">
              <rect
                x="-58"
                y="-14"
                width="116"
                height="28"
                rx="14"
                fill="#062A43"
                stroke="#FFFFFF"
                strokeWidth="2"
                filter="drop-shadow(0 3px 6px rgba(6,42,67,0.3))"
              />
              <text x="-40" y="3.5" fontSize="11">
                📍
              </text>
              <text
                x="4"
                y="4.5"
                textAnchor="middle"
                fill="#FFFFFF"
                fontSize="11.5"
                fontWeight="800"
                fontFamily="DM Sans, sans-serif"
              >
                {translations.youAreHere}
              </text>
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
};

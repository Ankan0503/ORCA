import React, { useRef, useState } from 'react';
import { LanguageOption } from '../types';
import { NavTabId, OrcaBottomNav } from '../components/OrcaBottomNav';
import { OrcaMapHeader } from '../components/map/OrcaMapHeader';
import { OrcaMapFilterBar, MapFilterType } from '../components/map/OrcaMapFilterBar';
import { OrcaMapLegend } from '../components/map/OrcaMapLegend';
import { OrcaMapControls } from '../components/map/OrcaMapControls';
import { OrcaMapCard } from '../components/map/OrcaMapCard';
import { OrcaMapZoneModal } from '../components/map/OrcaMapZoneModal';
import { OrcaLeafletMap, OrcaLeafletMapHandle } from '../components/map/OrcaLeafletMap';
import { getMapTranslations, MapZone, MAP_ZONES_CONFIG } from '../data/mapData';

interface MapPageProps {
  locationName?: string;
  onLocationClick?: () => void;
  currentLanguage?: LanguageOption;
  onNavigateHome?: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  onNavigateFindFish?: () => void;
  onNavigateSafety?: () => void;
  onNavigateAlerts?: () => void;
}

export const MapPage: React.FC<MapPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  onNavigateFindFish,
  onNavigateSafety,
  onNavigateAlerts,
  locationName,
  onLocationClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const translations = getMapTranslations(langCode);

  const [activeFilter, setActiveFilter] = useState<MapFilterType>('fishing');
  const [selectedZone, setSelectedZone] = useState<MapZone | null>(null);
  const [showRoute, setShowRoute] = useState<boolean>(true);
  const [isOffline, setIsOffline] = useState<boolean>(false);

  // Leaflet drives its own pan/zoom; the page controls call into it via this ref.
  const mapRef = useRef<OrcaLeafletMapHandle | null>(null);

  const handleZoomIn = () => {
    mapRef.current?.zoomIn();
  };

  const handleZoomOut = () => {
    mapRef.current?.zoomOut();
  };

  const handleResetLocation = () => {
    mapRef.current?.recenter();
    setShowRoute(true);
  };

  const handleSelectZone = (zone: MapZone) => {
    setSelectedZone(zone);
  };

  const handleRecommendationCardClick = () => {
    const bestZone = MAP_ZONES_CONFIG.find((z) => z.id === 'best-zone');
    if (bestZone) {
      setSelectedZone(bestZone);
    }
  };

  const handleNavigateAction = (route: 'find-fish' | 'safety') => {
    if (route === 'find-fish') {
      onNavigateFindFish?.();
    } else if (route === 'safety') {
      onNavigateSafety?.();
    }
  };

  return (
    <div
      className="relative w-full h-[100svh] h-[100dvh] overflow-hidden bg-[#E2F2FC] font-sans select-none flex flex-col"
      id="orca-map-page-screen"
    >
      {/* 
        1. FLOATING COMPACT TOP HEADER 
        - Back arrow to Home
        - ORCA logo
        - 📍 Digha, West Bengal
        - Offline & update status
      */}
      <OrcaMapHeader
          onLocationClick={onLocationClick}
        onBackClick={() => onNavigateHome?.()}
        currentLanguage={currentLanguage}
        isOffline={isOffline}
        onToggleOffline={() => setIsOffline(!isOffline)}
        locationName={locationName ?? translations.locationName}
      />

      {/* 
        2. HORIZONTAL FILTER CHIPS (Fishing | Safety | PFZ | Restrictions)
      */}
      <OrcaMapFilterBar
        activeFilter={activeFilter}
        onChangeFilter={setActiveFilter}
        translations={translations}
      />

      {/* 
        3. COMPACT FLOATING LEGEND (🟢 Best, 🟡 Good, 🔴 Avoid, ⚪ Restricted)
      */}
      <OrcaMapLegend translations={translations} />

      {/* 
        4. ESSENTIAL MAP CONTROLS (＋, −, GPS Re-center)
      */}
      <OrcaMapControls
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onResetLocation={handleResetLocation}
        translations={translations}
      />

      {/* 
        5. MAIN INTERACTIVE COASTAL MAP CANVAS
      */}
      <main className="w-full h-full flex-1 relative overflow-hidden" id="orca-map-canvas-main">
        <OrcaLeafletMap
          ref={mapRef}
          activeFilter={activeFilter}
          showRoute={showRoute}
          onSelectZone={handleSelectZone}
          selectedZoneId={selectedZone?.id}
          translations={translations}
        />
      </main>

      {/* 
        6. FLOATING BEST AREA RECOMMENDATION CARD
        - 🎣 Best fishing area • 12 km offshore
        - Good fishing chance • Safe to go
        - Arrow to Find Fish details
      */}
      <OrcaMapCard
        onCardClick={handleRecommendationCardClick}
        onNavigateToFindFish={() => onNavigateFindFish?.()}
        onToggleRoute={() => setShowRoute(!showRoute)}
        showRoute={showRoute}
        translations={translations}
      />

      {/* 
        7. ZONE DETAILS MODAL / BOTTOM SHEET
        - Pops up on zone tap (Restricted area shows "Fishing is not allowed here", Avoid shows storm risk, Best shows 12 km safe)
      */}
      <OrcaMapZoneModal
        zone={selectedZone}
        onClose={() => setSelectedZone(null)}
        onNavigateAction={handleNavigateAction}
        translations={translations}
      />

      {/* 
        8. PERSISTENT 5-ITEM BOTTOM NAVIGATION
      */}
      <OrcaBottomNav
        activeTab="map"
        onTabChange={(tab) => onNavigateTab?.(tab)}
        currentLanguage={currentLanguage}
      />
    </div>
  );
};

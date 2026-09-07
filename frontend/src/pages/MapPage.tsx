import React, { useEffect, useRef, useState } from 'react';
import { LanguageOption } from '../types';
import { NavTabId, OrcaBottomNav } from '../components/OrcaBottomNav';
import { OrcaMapHeader } from '../components/map/OrcaMapHeader';
import { OrcaMapFilterBar, MapFilterType } from '../components/map/OrcaMapFilterBar';
import { OrcaMapLegend } from '../components/map/OrcaMapLegend';
import { OrcaMapControls } from '../components/map/OrcaMapControls';
import { OrcaMapCard } from '../components/map/OrcaMapCard';
import { OrcaLeafletMap, OrcaLeafletMapHandle } from '../components/map/OrcaLeafletMap';
import { getMapTranslations } from '../data/mapData';
import {
  getPfzAdvisory,
  getGeofence,
  checkClosures,
  PfzAdvisory,
  GeofenceResult,
  ClosureCheck,
} from '../services/orcaApi';
import { OrcaBoundaryBadge } from '../components/map/OrcaBoundaryBadge';
import { OrcaRouteCard } from '../components/map/OrcaRouteCard';
import { getRoute, RoutePlan } from '../services/orcaApi';

interface MapPageProps {
  locationName?: string;
  latitude?: number;
  longitude?: number;
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
  latitude,
  longitude,
  onLocationClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const translations = getMapTranslations(langCode);

  const [activeFilter, setActiveFilter] = useState<MapFilterType>('fishing');
  const [isOffline, setIsOffline] = useState<boolean>(false);

  // The real INCOIS advisory for the user's coast, shown on the floating card.
  const [advisory, setAdvisory] = useState<PfzAdvisory | null>(null);
  // Where this position stands against India's maritime limits.
  const [geofence, setGeofence] = useState<GeofenceResult | null>(null);
  const [geofenceLoading, setGeofenceLoading] = useState<boolean>(true);
  // Fishing closures: the protected areas and the closed season. A boat can
  // break both on a calm day, so they ride along with the boundary check.
  const [closures, setClosures] = useState<ClosureCheck | null>(null);

  // The planned passage to the nearest advised ground, and the boat's own
  // position if the device will give one.
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null);
  const [routeLoading, setRouteLoading] = useState<boolean>(false);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [routeOpen, setRouteOpen] = useState<boolean>(false);
  const [livePosition, setLivePosition] = useState<{ latitude: number; longitude: number } | null>(
    null,
  );

  const planRoute = () => {
    if (latitude == null || longitude == null) return;
    setRouteOpen(true);
    setRouteLoading(true);
    setRouteError(null);
    getRoute(latitude, longitude, langCode)
      .then(setRoutePlan)
      .catch((err) => setRouteError(err?.message ?? 'Could not plan a route'))
      .finally(() => setRouteLoading(false));
  };

  // A real fix is used when the device gives one; otherwise the boat marker is
  // shown as a labelled preview rather than pretending to know where you are.
  useEffect(() => {
    if (!routeOpen || typeof navigator === 'undefined' || !navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (pos) =>
        setLivePosition({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => setLivePosition(null),
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 },
    );
    return () => navigator.geolocation.clearWatch(id);
  }, [routeOpen]);

  useEffect(() => {
    if (latitude == null || longitude == null) {
      setGeofenceLoading(false);
      return;
    }
    let cancelled = false;
    setGeofenceLoading(true);
    checkClosures(latitude, longitude)
      .then((result) => {
        if (!cancelled) setClosures(result);
      })
      .catch(() => {
        // The badge simply omits the closure rows rather than claiming the
        // water is open.
      });

    getGeofence(latitude, longitude)
      .then((result) => {
        if (!cancelled) setGeofence(result);
      })
      .catch(() => {
        // The badge shows a neutral checking state rather than claiming
        // the boat is safely inside Indian waters.
      })
      .finally(() => {
        if (!cancelled) setGeofenceLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [latitude, longitude]);

  useEffect(() => {
    if (latitude == null || longitude == null) return;
    let cancelled = false;
    getPfzAdvisory(latitude, longitude, langCode)
      .then((result) => {
        if (!cancelled) setAdvisory(result);
      })
      .catch(() => {
        // The card falls back to a neutral "loading" state rather than
        // inventing a recommendation.
      });
    return () => {
      cancelled = true;
    };
  }, [latitude, longitude, langCode]);

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
        LIVE MARITIME BOUNDARY STATUS
        Distance to the nearest foreign maritime boundary, from Marine Regions
        v12 geometry held on the server.
      */}
      <OrcaBoundaryBadge
        geofence={geofence}
        loading={geofenceLoading}
        closures={closures}
      />

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
          translations={translations}
          language={langCode}
          userLatitude={latitude}
          userLongitude={longitude}
          route={routeOpen ? routePlan?.route ?? null : null}
          livePosition={livePosition}
        />
      </main>

      {/* 
        6. FLOATING BEST AREA RECOMMENDATION CARD
        - 🎣 Best fishing area • 12 km offshore
        - Good fishing chance • Safe to go
        - Arrow to Find Fish details
      */}
      {routeOpen ? (
        <OrcaRouteCard
          plan={routePlan}
          loading={routeLoading}
          error={routeError}
          live={Boolean(livePosition)}
          onClose={() => {
            setRouteOpen(false);
            setRoutePlan(null);
            setRouteError(null);
          }}
        />
      ) : (
        <OrcaMapCard
          onCardClick={planRoute}
          onNavigateToFindFish={() => onNavigateFindFish?.()}
          translations={translations}
          advisory={advisory}
        />
      )}

      {/*
        7. Zone details are shown in the map's own popups, tapped straight on an
        INCOIS zone. The old bottom-sheet modal was removed with the invented
        best/good/avoid zones it described.
      */}

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

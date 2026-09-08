import React, { useEffect, useRef, useState } from 'react';
import { LanguageOption } from '../types';
import { NavTabId, OrcaBottomNav } from '../components/OrcaBottomNav';
import { OrcaMapHeader } from '../components/map/OrcaMapHeader';
import { OrcaMapFilterBar, MapLayerId, ALL_LAYERS } from '../components/map/OrcaMapFilterBar';
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
import { ChainPlan, getChainRoute, getRoute, RoutePlan } from '../services/orcaApi';
import { OrcaTripCard } from '../components/map/OrcaTripCard';
import { OrcaSteeringCard } from '../components/map/OrcaSteeringCard';
import { bearingBetween } from '../hooks/useCompassHeading';

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

  // Every layer starts on. The map's work was previously invisible until you
  // guessed which filter it hid behind; now it is all there and the chips take
  // things away rather than reveal them.
  const [activeLayers, setActiveLayers] = useState<MapLayerId[]>(ALL_LAYERS);

  const toggleLayer = (layer: MapLayerId) =>
    setActiveLayers((current) =>
      current.includes(layer) ? current.filter((l) => l !== layer) : [...current, layer],
    );
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

  // A trip across several grounds. Kept separate from the single-destination
  // route above: they answer different questions and a fisherman may want to
  // look at one ground closely while still holding a trip in progress.
  const [tripStops, setTripStops] = useState<
    { latitude: number; longitude: number; label: string }[]
  >([]);
  const [tripPlan, setTripPlan] = useState<ChainPlan | null>(null);
  const [tripLoading, setTripLoading] = useState<boolean>(false);
  const [tripError, setTripError] = useState<string | null>(null);
  const [tripOpen, setTripOpen] = useState<boolean>(false);
  const [tripReturn, setTripReturn] = useState<boolean>(true);

  // The steering instrument, and the bearing the boat is actually making good.
  // Track is derived from consecutive GPS fixes, which is the only way to get
  // it — and the reason the compass leads: a stopped boat has no track at all.
  const [steering, setSteering] = useState<boolean>(false);
  const [trackBearing, setTrackBearing] = useState<number | null>(null);
  const previousFix = useRef<{ latitude: number; longitude: number } | null>(null);
  const [livePosition, setLivePosition] = useState<{ latitude: number; longitude: number } | null>(
    null,
  );

  const addTripStop = (stopLat: number, stopLon: number, label: string) => {
    setTripOpen(true);
    // The plan is stale the moment the stops change — clearing it is what stops
    // an old verdict sitting under a new list of grounds.
    setTripPlan(null);
    setTripError(null);
    setTripStops((current) => {
      const alreadyThere = current.some(
        (s) =>
          Math.abs(s.latitude - stopLat) < 1e-4 && Math.abs(s.longitude - stopLon) < 1e-4,
      );
      if (alreadyThere || current.length >= 4) return current;
      return [...current, { latitude: stopLat, longitude: stopLon, label }];
    });
  };

  const planTrip = (
    stops = tripStops,
    includeReturn = tripReturn,
  ) => {
    if (latitude == null || longitude == null || stops.length === 0) return;
    setTripLoading(true);
    setTripError(null);
    getChainRoute(latitude, longitude, stops, { home: includeReturn, lang: langCode })
      .then(setTripPlan)
      .catch((err) => setTripError(err?.message ?? 'Could not plan this trip'))
      .finally(() => setTripLoading(false));
  };

  const planRoute = (destination?: { latitude: number; longitude: number }) => {
    if (latitude == null || longitude == null) return;
    setRouteOpen(true);
    setRouteLoading(true);
    setRouteError(null);
    getRoute(latitude, longitude, langCode, undefined, destination)
      .then(setRoutePlan)
      .catch((err) => setRouteError(err?.message ?? 'Could not plan a route'))
      .finally(() => setRouteLoading(false));
  };

  // A real fix is used when the device gives one; otherwise the boat marker is
  // shown as a labelled preview rather than pretending to know where you are.
  useEffect(() => {
    if (!routeOpen || typeof navigator === 'undefined' || !navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (pos) => {
        const next = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
        // A track bearing only means something once the boat has actually
        // moved. Below about 15 m the "movement" is GPS noise, and a bearing
        // taken from it would spin the drift readout at random.
        const previous = previousFix.current;
        if (previous) {
          const metres =
            Math.hypot(
              (next.latitude - previous.latitude) * 111_320,
              (next.longitude - previous.longitude) *
                111_320 *
                Math.cos((next.latitude * Math.PI) / 180),
            );
          if (metres >= 15) {
            setTrackBearing(
              bearingBetween(
                previous.latitude,
                previous.longitude,
                next.latitude,
                next.longitude,
              ),
            );
            previousFix.current = next;
          }
        } else {
          previousFix.current = next;
        }
        setLivePosition(next);
      },
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
        activeLayers={activeLayers}
        onToggleLayer={toggleLayer}
        translations={translations}
      />

      {/* 
        3. COMPACT FLOATING LEGEND (🟢 Best, 🟡 Good, 🔴 Avoid, ⚪ Restricted)
      */}
      <OrcaMapLegend translations={translations} activeLayers={activeLayers} />

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
          activeLayers={activeLayers}
          translations={translations}
          language={langCode}
          userLatitude={latitude}
          userLongitude={longitude}
          route={routeOpen ? routePlan?.route ?? null : null}
          livePosition={livePosition}
          onRouteTo={(destLat, destLon) => planRoute({ latitude: destLat, longitude: destLon })}
          onAddStop={addTripStop}
          chainStops={tripStops}
        />
      </main>

      {/* 
        6. FLOATING BEST AREA RECOMMENDATION CARD
        - 🎣 Best fishing area • 12 km offshore
        - Good fishing chance • Safe to go
        - Arrow to Find Fish details
      */}
      {steering && routePlan?.route.legs.length ? (
        <OrcaSteeringCard
          leg={routePlan.route.legs[0]}
          trackBearingDeg={trackBearing}
          language={langCode}
          onClose={() => setSteering(false)}
        />
      ) : null}

      {tripOpen && (
        <OrcaTripCard
          stops={tripStops}
          plan={tripPlan}
          loading={tripLoading}
          error={tripError}
          includeReturn={tripReturn}
          onToggleReturn={(value) => {
            setTripReturn(value);
            setTripPlan(null);
            if (tripStops.length) planTrip(tripStops, value);
          }}
          onRemoveStop={(index) => {
            const next = tripStops.filter((_, i) => i !== index);
            setTripStops(next);
            setTripPlan(null);
          }}
          onClear={() => {
            setTripStops([]);
            setTripPlan(null);
            setTripError(null);
          }}
          onPlan={() => planTrip()}
          onClose={() => setTripOpen(false)}
        />
      )}

      {routeOpen ? (
        <OrcaRouteCard
          plan={routePlan}
          loading={routeLoading}
          error={routeError}
          live={Boolean(livePosition)}
          onSteer={routePlan?.route.legs.length ? () => setSteering(true) : undefined}
          onClose={() => {
            setRouteOpen(false);
            setRoutePlan(null);
            setRouteError(null);
          }}
        />
      ) : tripOpen ? null : (
        <OrcaMapCard
          onCardClick={() => planRoute()}
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

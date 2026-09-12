import React, { useEffect, useState, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, TriangleAlert, Anchor, Volume2, VolumeX, Square } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';
import { ClosureCheck, GeofenceResult } from '../../services/orcaApi';
import { boundaryAlerts, BoundaryAlertState } from '../../services/audio/boundaryAlertService';
import { maritimeSiren } from '../../services/audio/maritimeSirenService';

/**
 * Live maritime-boundary status for the user's position.
 *
 * Crossing into Sri Lankan or Pakistani waters is one of the commonest ways
 * Indian fishermen are arrested, and it happens by drift far more often than by
 * intent. This badge keeps the distance to the nearest foreign boundary — and
 * whose it is — permanently in view.
 *
 * The distances behind the colours are ORCA's own caution margins, not a legal
 * limit; the badge says so on the warning states rather than implying an
 * official ruling.
 *
 * Now includes audio alerts: sirens + voice warnings for boundary breaches
 * and protected area incursions.
 */
interface OrcaBoundaryBadgeProps {
  geofence: GeofenceResult | null;
  loading: boolean;
  /**
   * Fishing closures for this position. A protected area and a closed season
   * are breaches a boat can commit on a calm, sunny day with a good catch
   * showing, so they belong beside the border warning rather than buried.
   */
  closures?: ClosureCheck | null;
  translations: MapTranslations;
}

const STYLES: Record<string, { bg: string; border: string; text: string }> = {
  critical: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  outside: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  beyond_eez: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  warning: { bg: 'bg-[#FFFBEB]', border: 'border-[#F5D68B]', text: 'text-[#92400E]' },
  watch: { bg: 'bg-[#F0F6FA]', border: 'border-[#BED6E6]', text: 'text-[#0C587F]' },
  clear: { bg: 'bg-[#F0FDF4]', border: 'border-[#A6DDB6]', text: 'text-[#166534]' },
  not_at_sea: { bg: 'bg-[#F0F6FA]', border: 'border-[#BED6E6]', text: 'text-[#0C587F]' },
};

export const OrcaBoundaryBadge: React.FC<OrcaBoundaryBadgeProps> = ({
  geofence,
  loading,
  closures,
  translations,
}) => {
  const [alertState, setAlertState] = useState<BoundaryAlertState>({
    level: 'clear',
    headline: '',
    detail: '',
    isSirenActive: false,
    isSpeaking: false,
  });
  const [isMuted, setIsMuted] = useState<boolean>(false);

  // Subscribe to boundary alert service state
  useEffect(() => {
    const unsub = boundaryAlerts.subscribe(setAlertState);
    return unsub;
  }, []);

  // Evaluate geofence + closures whenever they change
  useEffect(() => {
    if (!loading && geofence) {
      boundaryAlerts.evaluate(geofence, closures ?? null);
    }
  }, [geofence, closures, loading]);

  const handleToggleMute = useCallback(async () => {
    const next = !isMuted;
    setIsMuted(next);
    boundaryAlerts.setMuted(next);
    if (!next) {
      // Unmuting — unlock audio context
      await maritimeSiren.unlock();
    }
  }, [isMuted]);

  const handleListenAlert = useCallback(async () => {
    if (isMuted) {
      setIsMuted(false);
      boundaryAlerts.setMuted(false);
    }
    await maritimeSiren.unlock();
    await boundaryAlerts.speakCurrentState(geofence, closures ?? null);
  }, [geofence, closures, isMuted]);

  const handleStopAudio = useCallback(() => {
    boundaryAlerts.stopAll();
  }, []);

  const isAudioActive = alertState.isSirenActive || alertState.isSpeaking;

  if (loading || !geofence) {
    return (
      <div className="absolute bottom-[178px] sm:bottom-[190px] left-3 sm:left-4 right-3 sm:right-4 z-20 pointer-events-none max-w-[620px] mx-auto">
        <div className="rounded-xl bg-white/95 border border-[#D0DFEB] shadow-md px-2.5 py-1.5 font-ui text-[11.5px] text-[#557186]">
          {translations.ui.checkingWaters}
        </div>
      </div>
    );
  }

  const style = STYLES[geofence.level] ?? STYLES.watch;
  const alarming =
    geofence.level === 'critical' ||
    geofence.level === 'outside' ||
    geofence.level === 'beyond_eez';
  const isWarning = geofence.level === 'warning';
  const hasMpaAlert = closures?.insideProtectedArea || closures?.areas?.some((a) => !a.inside && a.distanceKm < 5);
  const showAudioControls = alarming || isWarning || hasMpaAlert;

  const Icon = alarming
    ? TriangleAlert
    : geofence.level === 'warning'
      ? ShieldAlert
      : geofence.level === 'not_at_sea'
        ? Anchor
        : ShieldCheck;

  const nearest = geofence.nearestBoundary;

  const headline = geofence.insideEez
    ? "Inside India\u2019s EEZ"
    : geofence.level === 'not_at_sea'
      ? 'In harbour / inshore'
      : geofence.level === 'beyond_eez'
        ? "Beyond India\u2019s EEZ"
        : "Outside India\u2019s EEZ";

  return (
    <div
      className="absolute bottom-[178px] sm:bottom-[190px] left-3 sm:left-4 right-3 sm:right-4 z-20 pointer-events-auto max-w-[620px] mx-auto"
      id="orca-boundary-badge"
    >
      <div
        className={`rounded-xl ${style.bg} border ${style.border} shadow-md px-3 py-2 flex items-center justify-between gap-3 ${
          isAudioActive ? 'ring-2 ring-red-400/60 shadow-lg shadow-red-200/30' : ''
        }`}
        title={geofence.message}
      >
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className={`flex items-center gap-1.5 font-ui font-bold text-[12.5px] ${style.text}`}>
            <Icon size={14} className={`stroke-[2.5] shrink-0 ${isAudioActive && alarming ? 'animate-pulse' : ''}`} />
            <span className="truncate">{headline}</span>
          </div>
          {(geofence.level === 'critical' || geofence.level === 'warning') && (
            <span className="font-ui text-[10px] text-[#6B7C8A] leading-[1.25]">
              {translations.ui.cautionMarginNote}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {nearest && (
            <div className="font-ui text-[11.5px] text-[#3E5C70] leading-[1.3] text-right">
              <div className="font-semibold">{nearest.neighbour}</div>
              <div>
                {nearest.distanceKm} km {nearest.bearing}
              </div>
            </div>
          )}

          {/* Audio controls for active alerts */}
          {showAudioControls && (
            <div className="flex items-center gap-1 ml-1">
              {isAudioActive ? (
                <button
                  type="button"
                  onClick={handleStopAudio}
                  className="w-8 h-8 rounded-lg bg-red-100 border border-red-300 flex items-center justify-center active:scale-95 transition-all cursor-pointer"
                  title="Stop audio"
                  aria-label="Stop audio alert"
                >
                  <Square size={12} className="text-red-600 fill-current" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleListenAlert}
                  className={`w-8 h-8 rounded-lg border flex items-center justify-center active:scale-95 transition-all cursor-pointer ${
                    alarming
                      ? 'bg-red-50 border-red-300 text-red-600'
                      : 'bg-amber-50 border-amber-300 text-amber-700'
                  }`}
                  title="Listen to boundary warning"
                  aria-label="Play boundary alert"
                >
                  <Volume2 size={14} className="stroke-[2.5]" />
                </button>
              )}

              <button
                type="button"
                onClick={handleToggleMute}
                className={`w-7 h-7 rounded-lg border flex items-center justify-center transition-all cursor-pointer ${
                  isMuted
                    ? 'bg-gray-100 border-gray-300 text-gray-400'
                    : 'bg-white border-gray-200 text-gray-600'
                }`}
                title={isMuted ? 'Unmute alerts' : 'Mute alerts'}
                aria-label={isMuted ? 'Unmute boundary alerts' : 'Mute boundary alerts'}
              >
                {isMuted ? <VolumeX size={12} /> : <Volume2 size={10} className="opacity-50" />}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Inside a sanctuary — the most serious of these, so it sits first. */}
      {closures?.insideProtectedArea && (
        <div className={`mt-1.5 rounded-xl bg-[#F5F3FF] border border-[#C4B5FD] px-3 py-2 ${
          isAudioActive ? 'ring-2 ring-purple-400/50' : ''
        }`}>
          <div className="font-ui font-bold text-[12.5px] text-[#5B21B6] flex items-center justify-between">
            <span>{translations.ui.insideProtectedArea}</span>
            {!isAudioActive && (
              <button
                type="button"
                onClick={handleListenAlert}
                className="w-7 h-7 rounded-lg bg-purple-100 border border-purple-300 flex items-center justify-center active:scale-95 transition-all cursor-pointer"
                title="Listen to MPA warning"
                aria-label="Play MPA alert"
              >
                <Volume2 size={12} className="text-purple-600 stroke-[2.5]" />
              </button>
            )}
          </div>
          <div className="font-ui text-[11px] text-[#4C3D8F] leading-[1.3]">
            {closures.areas.filter((a) => a.inside).map((a) => a.name).join(', ')} —
            fishing here is restricted.
          </div>
        </div>
      )}

      {/* The annual closed season. */}
      {closures?.fishingBan.active && (
        <div className="mt-1.5 rounded-xl bg-[#FFFBEB] border border-[#F5D68B] px-3 py-2">
          <div className="font-ui font-bold text-[12.5px] text-[#92400E]">
            {translations.ui.fishingBanInForce}
          </div>
          <div className="font-ui text-[11px] text-[#6B5423] leading-[1.3]">
            {closures.fishingBan.message}
          </div>
        </div>
      )}
    </div>
  );
};

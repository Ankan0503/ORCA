import React from 'react';
import { AlertTriangle, CheckCircle2, Clock, MapPin, Route, Trash2, X } from 'lucide-react';
import { MapTranslations } from '../../data/mapData';
import { ChainPlan } from '../../services/orcaApi';

/**
 * A trip across several grounds, and whether it fits before the sea turns.
 *
 * The single-destination route card answers "can I get there". This answers the
 * question that actually decides the day, and which routing to one destination
 * could never reach: *can I work these grounds and still get home*. The passage
 * back is usually the longest leg of the trip and it was never counted before —
 * which is why the interesting verdict is not "no" but "the second ground fits,
 * the way home does not".
 *
 * The stop list is therefore shown with a per-stop verdict rather than one
 * overall answer. A red mark against "Home" is a different instruction from a
 * red mark against "Ground 1", and a fisherman needs to see which he has.
 */

const VERDICT_STYLE: Record<
  ChainPlan['safety']['verdict'],
  { bg: string; border: string; text: string; icon: React.ReactNode; title: string }
> = {
  fits: {
    bg: '#F0FDF4',
    border: '#86EFAC',
    text: '#166534',
    icon: <CheckCircle2 size={18} className="text-[#16A34A] shrink-0" />,
    title: 'The trip fits',
  },
  partly_fits: {
    bg: '#FFFBEB',
    border: '#FCD34D',
    text: '#92400E',
    icon: <AlertTriangle size={18} className="text-[#D97706] shrink-0" />,
    title: 'Only part of the trip fits',
  },
  does_not_fit: {
    bg: '#FEF2F2',
    border: '#FCA5A5',
    text: '#991B1B',
    icon: <AlertTriangle size={18} className="text-[#DC2626] shrink-0" />,
    title: 'This trip does not fit',
  },
};

const clock = (iso: string): string => iso.slice(11, 16);

interface OrcaTripCardProps {
  stops: { latitude: number; longitude: number; label: string }[];
  plan: ChainPlan | null;
  loading: boolean;
  error: string | null;
  includeReturn: boolean;
  onToggleReturn: (value: boolean) => void;
  onRemoveStop: (index: number) => void;
  onClear: () => void;
  onPlan: () => void;
  onClose: () => void;
  translations: MapTranslations;
}

export const OrcaTripCard: React.FC<OrcaTripCardProps> = ({
  stops,
  plan,
  loading,
  error,
  includeReturn,
  onToggleReturn,
  onRemoveStop,
  onClear,
  onPlan,
  onClose,
  translations,
}) => {
  const verdict = plan ? VERDICT_STYLE[plan.safety.verdict] : null;

  return (
    <section
      className="absolute left-2.5 right-2.5 sm:left-4 sm:right-4 bottom-[92px] sm:bottom-[104px] z-30 pointer-events-auto"
      aria-label={translations.ui.tripAcrossGrounds}
      id="orca-trip-card"
    >
      <div className="bg-white/97 backdrop-blur-md border border-[#D0DFEB] rounded-2xl shadow-lg p-3 sm:p-3.5 flex flex-col gap-2.5 max-h-[58vh] overflow-y-auto">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-ui font-bold text-[15px] text-[#062A43] flex items-center gap-1.5">
            <Route size={16} className="text-[#0B4A34]" />
            {translations.ui.yourTrip}
            <span className="font-normal text-[12px] text-[#8AA0B0]">
              {stops.length} ground{stops.length === 1 ? '' : 's'}
            </span>
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={translations.ui.closeTripPlanner}
            className="p-1 rounded-lg text-[#557186] hover:bg-[#EEF5FA]"
          >
            <X size={16} />
          </button>
        </div>

        {/* The grounds, in the order they will be worked. */}
        <ol className="flex flex-col gap-1" role="list">
          {stops.map((stop, index) => {
            const leg = plan?.stops.find((s) => s.index === index);
            return (
              <li
                key={`${stop.latitude},${stop.longitude},${index}`}
                className="flex items-center gap-2 text-[12.5px] font-ui"
              >
                <span className="w-5 h-5 rounded-full bg-[#0B4A34] text-white font-bold text-[11px] flex items-center justify-center shrink-0">
                  {index + 1}
                </span>
                <span className="flex-1 text-[#062A43] truncate">{stop.label}</span>
                {leg && (
                  <span
                    className={`font-semibold tabular-nums ${
                      leg.withinSafeWindow ? 'text-[#166534]' : 'text-[#B91C1C]'
                    }`}
                  >
                    {clock(leg.arrivalAt)}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveStop(index)}
                  aria-label={`Remove ${stop.label} from the trip`}
                  className="p-1 rounded text-[#8AA0B0] hover:text-[#B91C1C]"
                >
                  <Trash2 size={13} />
                </button>
              </li>
            );
          })}

          {includeReturn && (
            <li className="flex items-center gap-2 text-[12.5px] font-ui pt-1 border-t border-[#EEF5FA] mt-0.5">
              <span className="w-5 h-5 rounded-full bg-[#EEF5FA] text-[#557186] font-bold text-[11px] flex items-center justify-center shrink-0">
                <MapPin size={11} />
              </span>
              <span className="flex-1 text-[#557186]">{translations.ui.backToStart}</span>
              {plan?.stops.find((s) => s.kind === 'home') && (
                <span
                  className={`font-semibold tabular-nums ${
                    plan.stops.find((s) => s.kind === 'home')!.withinSafeWindow
                      ? 'text-[#166534]'
                      : 'text-[#B91C1C]'
                  }`}
                >
                  {clock(plan.stops.find((s) => s.kind === 'home')!.arrivalAt)}
                </span>
              )}
            </li>
          )}
        </ol>

        <label className="flex items-center gap-2 font-ui text-[12px] text-[#557186] cursor-pointer">
          <input
            type="checkbox"
            checked={includeReturn}
            onChange={(e) => onToggleReturn(e.target.checked)}
            className="accent-[#0B4A34]"
          />
          {translations.ui.countPassageHome}
        </label>

        {/* The verdict. */}
        {loading && (
          <p className="font-ui text-[12.5px] text-[#557186]">{translations.ui.planningEachLeg}</p>
        )}

        {error && !loading && (
          <p className="font-ui text-[12.5px] text-[#B91C1C]">{error}</p>
        )}

        {plan && verdict && !loading && (
          <div
            className="rounded-xl border p-2.5 flex flex-col gap-1.5"
            style={{ background: verdict.bg, borderColor: verdict.border }}
          >
            <div className="flex items-center gap-1.5">
              {verdict.icon}
              <span className="font-ui font-bold text-[13.5px]" style={{ color: verdict.text }}>
                {verdict.title}
              </span>
            </div>
            <p className="font-ui text-[12.5px] leading-[1.45]" style={{ color: verdict.text }}>
              {plan.safety.message}
            </p>
            <div className="flex items-center gap-3 font-ui text-[11.5px] text-[#557186] pt-0.5">
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {plan.totals.hours.toFixed(1)} h
              </span>
              <span>{plan.totals.distanceKm.toFixed(0)} km</span>
              <span>at {plan.boatSpeedKmh} km/h</span>
            </div>
            <p className="font-ui text-[11px] text-[#7A8894] leading-[1.4]">
              {plan.safety.basis}
            </p>
          </div>
        )}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPlan}
            disabled={stops.length === 0 || loading}
            className="flex-1 font-ui font-bold text-[13px] py-2.5 rounded-xl bg-[#0B4A34] text-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {plan ? 'Re-check the trip' : 'Check this trip'}
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={stops.length === 0}
            className="font-ui font-bold text-[13px] px-3 py-2.5 rounded-xl border border-[#D0DFEB] text-[#557186] disabled:opacity-40"
          >
            Clear
          </button>
        </div>

        {stops.length === 0 && (
          <p className="font-ui text-[11.5px] text-[#8AA0B0] leading-[1.4]">
            {translations.ui.tapZoneAndChoose} <b>{translations.ui.addToTrip}</b>
            several grounds.
          </p>
        )}
      </div>
    </section>
  );
};

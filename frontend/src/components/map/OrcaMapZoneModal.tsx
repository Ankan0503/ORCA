import React from 'react';
import { X, ArrowRight, AlertTriangle, CheckCircle2, ShieldAlert, Compass } from 'lucide-react';
import { MapZone, MapTranslations } from '../../data/mapData';

interface OrcaMapZoneModalProps {
  zone: MapZone | null;
  onClose: () => void;
  onNavigateAction?: (route: 'find-fish' | 'safety') => void;
  translations: MapTranslations;
}

export const OrcaMapZoneModal: React.FC<OrcaMapZoneModalProps> = ({
  zone,
  onClose,
  onNavigateAction,
  translations,
}) => {
  if (!zone) return null;

  const isRestricted = zone.type === 'restricted';
  const isAvoid = zone.type === 'avoid';
  const isBest = zone.type === 'best';
  const isGood = zone.type === 'good';

  return (
    <div
      className="fixed inset-0 z-50 bg-black/45 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4 animate-fade-in select-none"
      id="orca-zone-details-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="orca-zone-title"
    >
      <div
        className="w-full max-w-[500px] bg-white rounded-t-[28px] sm:rounded-3xl p-5 min-[390px]:p-6 shadow-2xl flex flex-col gap-3.5 border border-[#D5E5F0] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
        id="orca-zone-details-sheet"
      >
        {/* Header: Zone Badge + Close Button */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`w-3.5 h-3.5 rounded-full ${
                isBest
                  ? 'bg-[#16A34A]'
                  : isGood
                  ? 'bg-[#EAB308]'
                  : isAvoid
                  ? 'bg-[#DC2626]'
                  : 'bg-[#94A3B8] border-2 border-dashed border-[#475569]'
              }`}
              aria-hidden="true"
            />
            <h3
              id="orca-zone-title"
              className="font-ui font-extrabold text-[18px] min-[390px]:text-[20px] text-[#062A43] leading-tight"
            >
              {isRestricted
                ? translations.restrictedWarning
                : isAvoid
                ? translations.avoidWarning
                : isBest
                ? translations.bestCard.title
                : zone.name}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            id="orca-zone-close-btn"
            aria-label="Close details"
            className="w-[36px] h-[36px] rounded-full bg-[#F0F6FA] text-[#557186] hover:text-[#062A43] hover:bg-[#E2EDF5] flex items-center justify-center transition-colors cursor-pointer"
          >
            <X size={20} className="stroke-[2.4]" />
          </button>
        </div>

        {/* Primary Message in Large Clear Typography */}
        <div
          className={`p-3.5 rounded-2xl border ${
            isRestricted
              ? 'bg-[#F8FAFC] border-[#CBD5E1] text-[#334155]'
              : isAvoid
              ? 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]'
              : isBest
              ? 'bg-[#F0FDF4] border-[#BBF7D0] text-[#166534]'
              : 'bg-[#FEFCE8] border-[#FEF08A] text-[#854D0E]'
          }`}
        >
          {isRestricted ? (
            <div className="flex items-start gap-2.5">
              <ShieldAlert size={22} className="text-[#64748B] shrink-0 mt-0.5" />
              <div>
                <p className="font-ui font-bold text-[16px] text-[#1E293B]">
                  “{translations.fishingNotAllowed}”
                </p>
                <p className="font-ui text-[13px] text-[#64748B] mt-1 leading-snug">
                  Protected conservation & shipping fairway zone. Entry for commercial or traditional fishing is prohibited.
                </p>
              </div>
            </div>
          ) : isAvoid ? (
            <div className="flex items-start gap-2.5">
              <AlertTriangle size={22} className="text-[#DC2626] shrink-0 mt-0.5" />
              <div>
                <p className="font-ui font-bold text-[16px] text-[#991B1B]">
                  “Avoid area • Strong wind & waves after 2 PM.”
                </p>
                <p className="font-ui text-[13px] text-[#B91C1C] mt-1 leading-snug">
                  Shifting sandbars with sudden swells exceeding 2.2m. Stay at least 5 km clear of this perimeter.
                </p>
              </div>
            </div>
          ) : isBest ? (
            <div className="flex items-start gap-2.5">
              <CheckCircle2 size={22} className="text-[#16A34A] shrink-0 mt-0.5" />
              <div>
                <p className="font-ui font-extrabold text-[16px] text-[#15803D]">
                  “12 km offshore. Good fishing. Safe to go.”
                </p>
                <p className="font-ui text-[13px] text-[#166534] mt-1 leading-snug">
                  Optimal sea conditions and high chlorophyll front. Calm waters until 2 PM.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2.5">
              <Compass size={22} className="text-[#CA8A04] shrink-0 mt-0.5" />
              <div>
                <p className="font-ui font-bold text-[16px] text-[#854D0E]">
                  “18 km offshore. Moderate catch. Return before 2 PM.”
                </p>
                <p className="font-ui text-[13px] text-[#A16207] mt-1 leading-snug">
                  Favorable tidal current corridor. Keep watch on the rising south swell in the afternoon.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Action button */}
        <div className="pt-1 w-full">
          {isBest ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                onNavigateAction?.('find-fish');
              }}
              id="orca-zone-action-find-fish"
              className="w-full py-3.5 px-4 rounded-2xl bg-[#062A43] hover:bg-[#06365A] active:scale-[0.99] text-white font-ui font-bold text-[15px] flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer"
            >
              <span>View Spot Details in Find Fish</span>
              <ArrowRight size={18} className="stroke-[2.5]" />
            </button>
          ) : isAvoid ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                onNavigateAction?.('safety');
              }}
              id="orca-zone-action-safety"
              className="w-full py-3.5 px-4 rounded-2xl bg-[#DC2626] hover:bg-[#B91C1C] active:scale-[0.99] text-white font-ui font-bold text-[15px] flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer"
            >
              <span>Check Marine Safety Advisory</span>
              <ArrowRight size={18} className="stroke-[2.5]" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              id="orca-zone-action-close"
              className="w-full py-3 px-4 rounded-2xl bg-[#F0F6FA] hover:bg-[#E2EDF5] text-[#062A43] font-ui font-bold text-[15px] transition-colors cursor-pointer"
            >
              Back to Map
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

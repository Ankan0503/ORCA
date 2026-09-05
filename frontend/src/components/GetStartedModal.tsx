import React, { useState } from 'react';
import { X, ArrowRight, ShieldCheck, Waves, Phone, MapPin, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { LanguageOption } from '../types';

interface GetStartedModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: LanguageOption;
  onSuccess?: (harbor: string) => void;
}

const COASTAL_HARBORS = [
  'Chennai (Royapuram / Kasimedu), TN',
  'Visakhapatnam Harbor, AP',
  'Kochi (Thoppumpady), Kerala',
  'Sassoon Dock (Mumbai), Maharashtra',
  'Veraval Harbor, Gujarat',
  'Paradip Port, Odisha',
  'Mangalore Old Port, Karnataka',
  'Kanyakumari / Colachel, TN',
  'Digha / Shankarpur, West Bengal',
  'Rameswaram / Mandapam, TN',
];

export const GetStartedModal: React.FC<GetStartedModalProps> = ({
  isOpen,
  onClose,
  language,
  onSuccess,
}) => {
  const [phone, setPhone] = useState('');
  const [selectedHarbor, setSelectedHarbor] = useState(COASTAL_HARBORS[0]);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phone.trim().length >= 10) {
      setIsSubmitted(true);
    }
  };

  const handleReset = () => {
    setIsSubmitted(false);
    setPhone('');
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-[#031B2B]/60 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          id="orca-get-started-modal"
        >
          {/* Backdrop click */}
          <div className="absolute inset-0" onClick={handleReset} />

          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="relative w-full sm:max-w-lg bg-[#FAF8F5] rounded-t-3xl sm:rounded-2xl shadow-2xl p-6 sm:p-8 z-10 border border-[#062A43]/10 max-h-[92svh] overflow-y-auto"
          >
            {/* Close Button */}
            <button
              onClick={handleReset}
              className="absolute top-5 right-5 w-11 h-11 flex items-center justify-center rounded-full bg-[#062A43]/5 hover:bg-[#062A43]/10 text-[#062A43] transition-colors cursor-pointer focus:outline-hidden"
              aria-label="Close dialog"
            >
              <X size={20} />
            </button>

            {!isSubmitted ? (
              <div>
                {/* Header */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#1677A8]/10 text-[#1677A8] text-xs font-semibold tracking-wider uppercase font-ui">
                    <Waves size={13} />
                    Coastal Access
                  </span>
                </div>

                <h2 className="font-display text-3xl sm:text-4xl text-[#062A43] font-medium leading-tight mb-2">
                  Begin with ORCA
                </h2>
                <p className="font-ui text-sm sm:text-base text-[#062A43]/75 leading-relaxed mb-6">
                  Real-time sea state, wind conditions, and safety advisories for your harbor. Built specifically for fishermen.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4 font-ui">
                  {/* Harbor selection */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#062A43]/80 mb-1.5 flex items-center gap-1.5">
                      <MapPin size={14} className="text-[#1677A8]" />
                      Home Port / Landing Center
                    </label>
                    <select
                      value={selectedHarbor}
                      onChange={(e) => setSelectedHarbor(e.target.value)}
                      className="w-full h-12 px-3.5 rounded-xl bg-white border border-[#062A43]/20 text-[#062A43] text-base sm:text-sm focus:outline-hidden focus:border-[#062A43] focus:ring-1 focus:ring-[#062A43] transition-all cursor-pointer"
                    >
                      {COASTAL_HARBORS.map((harbor) => (
                        <option key={harbor} value={harbor}>
                          {harbor}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Mobile Number */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#062A43]/80 mb-1.5 flex items-center gap-1.5">
                      <Phone size={14} className="text-[#1677A8]" />
                      Mobile Number (For Sea Weather Bulletins)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-medium text-[#062A43]/60">
                        +91
                      </span>
                      <input
                        type="tel"
                        required
                        pattern="[0-9]{10}"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                        placeholder="Enter 10-digit number"
                        className="w-full h-12 pl-13 pr-4 rounded-xl bg-white border border-[#062A43]/20 text-[#062A43] text-base sm:text-sm focus:outline-hidden focus:border-[#062A43] focus:ring-1 focus:ring-[#062A43] transition-all"
                      />
                    </div>
                    <p className="text-[12px] text-[#062A43]/60 mt-1">
                      Works over standard cellular SMS when data networks are unavailable offshore.
                    </p>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={phone.length < 10}
                    className="w-full h-14 mt-4 rounded-full bg-[#062A43] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#031B2B] text-white font-ui font-semibold text-base flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md active:scale-98"
                  >
                    <span>Connect My Harbor</span>
                    <ArrowRight size={18} />
                  </button>

                  <div className="flex items-center justify-center gap-2 pt-2 text-[12px] text-[#062A43]/70">
                    <ShieldCheck size={14} className="text-[#1677A8]" />
                    <span>Free service for Indian artisanal and mechanized fishermen</span>
                  </div>
                </form>
              </div>
            ) : (
              /* Success State */
              <div className="text-center py-4 font-ui">
                <div className="w-16 h-16 bg-[#1677A8]/10 text-[#1677A8] rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={32} />
                </div>
                <h3 className="font-display text-3xl text-[#062A43] font-medium mb-2">
                  Harbor Connected
                </h3>
                <p className="text-sm text-[#062A43]/80 leading-relaxed max-w-sm mx-auto mb-6">
                  You are now registered for marine intelligence and safety advisories at{' '}
                  <span className="font-semibold text-[#062A43]">{selectedHarbor}</span>.
                </p>
                <div className="p-4 bg-white rounded-xl border border-[#062A43]/10 text-left text-xs text-[#062A43]/85 space-y-1 mb-6">
                  <p>• Daily sea-state & wave condition forecast</p>
                  <p>• High-wind and cyclone alert notifications</p>
                  <p>• Communication configured in {language.nativeName} ({language.name})</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const harbor = selectedHarbor;
                    handleReset();
                    if (onSuccess) {
                      onSuccess(harbor);
                    }
                  }}
                  className="w-full h-12 rounded-full bg-[#062A43] text-white font-medium text-sm transition-colors hover:bg-[#031B2B] cursor-pointer"
                >
                  Enter Sea Operations
                </button>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

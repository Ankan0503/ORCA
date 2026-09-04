import React from 'react';
import { X, Anchor, Shield, Compass } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ModalType } from '../types';

interface EditorialInfoModalProps {
  type: ModalType;
  onClose: () => void;
}

export const EditorialInfoModal: React.FC<EditorialInfoModalProps> = ({ type, onClose }) => {
  if (!type || type === 'get-started') return null;

  const contentMap = {
    about: {
      tag: 'Marine Intelligence',
      icon: Compass,
      title: 'About ORCA',
      body1:
        'ORCA was conceived with one fundamental purpose: to bring the wisdom of oceanic science, satellite telemetry, and real-time meteorology directly to coastal fishermen across India.',
      body2:
        'Built with data from Earth observation satellites, oceanographic sensors, and coastal wave buoys, ORCA translates complex marine data into immediate, life-preserving clarity—accessible on ordinary mobile phones even in challenging coastal environments.',
    },
    'how-it-helps': {
      tag: 'Practical Utility',
      icon: Anchor,
      title: 'How ORCA Helps',
      body1:
        'Every voyage carries uncertainty. ORCA provides precision insight into wave swell heights, surface current velocities, wind shifts, and high-probability fishing zones before you untie your boat.',
      body2:
        'By helping fishermen chart safer routes and reach productive grounds with less fuel burned, ORCA protects both livelihoods and families waiting on the shore.',
    },
    safety: {
      tag: 'Preserving Lives',
      icon: Shield,
      title: 'Safety at Sea',
      body1:
        'The sea demands reverence. ORCA tracks sudden weather anomalies, squalls, and rough sea states, sending timely warnings before conditions deteriorate beyond safe thresholds.',
      body2:
        'Features include maritime boundary alerts, geofencing assistance, and low-bandwidth distress signaling, ensuring every fisherman has a guardian companion on the open water.',
    },
  };

  const current = contentMap[type];
  if (!current) return null;
  const Icon = current.icon;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#031B2B]/60 backdrop-blur-sm font-ui"
        role="dialog"
        aria-modal="true"
      >
        <div className="absolute inset-0" onClick={onClose} />
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 15, scale: 0.98 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className="relative w-full max-w-lg bg-[#FAF8F5] rounded-2xl shadow-2xl p-6 sm:p-8 z-10 border border-[#062A43]/10"
        >
          <button
            onClick={onClose}
            className="absolute top-5 right-5 w-10 h-10 flex items-center justify-center rounded-full bg-[#062A43]/5 hover:bg-[#062A43]/10 text-[#062A43] transition-colors cursor-pointer focus:outline-hidden"
            aria-label="Close"
          >
            <X size={18} />
          </button>

          <div className="flex items-center gap-2 mb-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#1677A8]/10 text-[#1677A8] text-xs font-semibold tracking-wider uppercase">
              <Icon size={13} />
              {current.tag}
            </span>
          </div>

          <h3 className="font-display text-3xl sm:text-4xl text-[#062A43] font-medium leading-tight mb-4">
            {current.title}
          </h3>

          <div className="space-y-3 text-[#062A43]/80 text-sm sm:text-base leading-relaxed">
            <p>{current.body1}</p>
            <p>{current.body2}</p>
          </div>

          <div className="mt-6 pt-4 border-t border-[#062A43]/10 flex justify-end">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-full bg-[#062A43] text-white text-sm font-medium hover:bg-[#031B2B] transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

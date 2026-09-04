import React, { useState, useEffect } from 'react';
import { ArrowLeft, LogOut, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import { getStoredUser, logoutUser, GoogleUser } from '../data/auth';

const ORCA_LOGO = '/assets/orca-logo.svg';
// Reusing the existing watercolor background from other ORCA pages
const BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface ProfilePageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  onNavigateLanding: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  onNavigateLanding,
}) => {
  const [user, setUser] = useState<GoogleUser | null>(getStoredUser);
  const [imageError, setImageError] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // If user is not authenticated, redirect to the existing login/landing page
  useEffect(() => {
    if (!user || !user.isAuthenticated) {
      onNavigateLanding();
    }
  }, [user, onNavigateLanding]);

  const handleTabChange = (tabId: NavTabId) => {
    if (tabId === 'profile') {
      // already on profile
      return;
    }
    if (tabId === 'home') {
      onNavigateHome();
    } else {
      onNavigateTab?.(tabId);
    }
  };

  const handleConfirmLogout = () => {
    logoutUser();
    setUser(null);
    setShowLogoutConfirm(false);
    onNavigateLanding();
  };

  if (!user || !user.isAuthenticated) {
    return null;
  }

  const initial = user.name ? user.name.trim().charAt(0).toUpperCase() : 'U';

  return (
    <div
      className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-x-hidden bg-[#F7FAFC] text-[#062A43] flex flex-col justify-between select-none"
      id="orca-profile-page"
    >
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reusing /assets/orca_safety_background.avif as requested
        - Soft opacity and gradients preserving generous negative space
        ===================================================================
      */}
      <div
        className="pointer-events-none absolute top-0 right-0 z-0 w-[240px] min-[390px]:w-[320px] sm:w-[440px] md:w-[520px] max-w-[70%] h-[300px] min-[390px]:h-[380px] sm:h-[430px] overflow-hidden select-none"
        aria-hidden="true"
      >
        <img
          src={BACKGROUND_IMAGE}
          alt=""
          className="w-full h-full object-cover object-top-right opacity-90 mix-blend-multiply"
          loading="eager"
          decoding="async"
        />
        {/* Soft edge feathering so the foreground remains clean and readable */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#F7FAFC] via-[#F7FAFC]/55 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#F7FAFC] via-transparent to-transparent" />
      </div>

      {/* 
        ===================================================================
        PAGE CONTAINER
        - Centered column, spacious layout
        - Optimized for 360x800, 390x844, 430x932
        - Safe-area bottom padding for the fixed bottom navigation
        ===================================================================
      */}
      <div className="relative z-10 w-full max-w-[520px] mx-auto px-4 min-[390px]:px-6 pt-3 sm:pt-5 pb-32 sm:pb-36 flex flex-col items-stretch flex-1">
        
        {/* 
          -----------------------------------------------------------------
          TOP HEADER
          Show: ←   ORCA
          Simple back arrow + unboxed logo, no large location selector
          -----------------------------------------------------------------
        */}
        <header
          className="w-full flex items-center justify-between gap-3 pt-1 pb-3"
          id="orca-profile-header"
          aria-label="Profile navigation header"
        >
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onNavigateHome}
              id="orca-profile-back-btn"
              aria-label="Go back to Home"
              className="w-[44px] h-[44px] rounded-full bg-white/90 backdrop-blur-md border border-[#D8E6F0] text-[#062A43] shadow-xs flex items-center justify-center hover:bg-white active:scale-95 transition-all duration-150 cursor-pointer focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#062A43]/30 shrink-0"
            >
              <ArrowLeft size={20} className="text-[#062A43] stroke-[2.4]" />
            </button>

            {/* ORCA Logo */}
            <div className="shrink-0 flex items-center">
              <img
                src={ORCA_LOGO}
                alt="ORCA"
                className="w-[100px] min-[390px]:w-[108px] h-auto object-contain block"
              />
            </div>
          </div>
        </header>

        {/* 
          -----------------------------------------------------------------
          PAGE TITLE
          - Cormorant Garamond heading: "My Profile"
          - Small DM Sans text: "Your ORCA account"
          -----------------------------------------------------------------
        */}
        <div className="w-full mt-3 sm:mt-5 mb-6 sm:mb-8 flex flex-col items-start">
          <h1
            className="font-display font-bold text-[34px] min-[390px]:text-[38px] sm:text-[44px] text-[#062A43] leading-[1.05] tracking-tight"
            id="orca-profile-title"
          >
            My Profile
          </h1>
          <p className="font-ui font-normal text-[14px] min-[390px]:text-[15px] text-[#5A7184] leading-normal mt-1.5">
            Your ORCA account
          </p>
        </div>

        {/* 
          -----------------------------------------------------------------
          PROFILE CARD (ONE centered card)
          Inside:
          - Google Profile Picture (90-100px, circular, subtle shadow/border)
          - User Name (~24px, bold)
          - Google Account Email (~14px, muted blue-gray)
          -----------------------------------------------------------------
        */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="w-full bg-white/95 backdrop-blur-sm rounded-[24px] sm:rounded-[28px] p-7 sm:p-9 shadow-[0_4px_24px_rgba(6,42,67,0.06)] border border-[#E2ECF4] flex flex-col items-center text-center"
          id="orca-profile-card"
        >
          {/* Google Profile Picture */}
          <div className="relative w-[96px] h-[96px] rounded-full shrink-0 flex items-center justify-center select-none shadow-[0_6px_20px_rgba(6,42,67,0.12)] border-2 border-white ring-1 ring-[#06365A]/10 bg-[#E8F2F8] overflow-hidden">
            {user.photoUrl && !imageError ? (
              <img
                src={user.photoUrl}
                alt={`${user.name}'s Google profile photo`}
                referrerPolicy="no-referrer"
                onError={() => setImageError(true)}
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <div
                className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#0B4F71] to-[#062A43] text-white font-ui font-bold text-[36px]"
                aria-label={`${user.name}'s avatar initial`}
              >
                {initial}
              </div>
            )}
          </div>

          {/* User Display Name */}
          <h2 className="font-ui font-bold text-[24px] text-[#062A43] mt-5 leading-tight tracking-tight px-2 break-words">
            {user.name}
          </h2>

          {/* Google Account Email */}
          <p className="font-ui font-normal text-[14px] text-[#607D94] mt-1.5 leading-normal break-all px-2">
            {user.email}
          </p>
        </motion.div>

        {/* 
          -----------------------------------------------------------------
          LOGOUT BUTTON
          - Below profile card
          - Full-width within content area
          - ~52px height
          - Rounded corners
          - Pale red/pink background
          - Red logout icon + red text
          - Accessible label & >= 44px touch target
          -----------------------------------------------------------------
        */}
        <div className="w-full mt-5 sm:mt-6">
          <button
            type="button"
            id="orca-logout-button"
            onClick={() => setShowLogoutConfirm(true)}
            aria-label="Log out of your ORCA account"
            className="w-full h-[52px] rounded-2xl bg-[#FEECEC] hover:bg-[#FDDCDC] active:scale-[0.98] border border-[#FCA5A5]/35 text-[#DC2626] font-ui font-semibold text-[15px] flex items-center justify-center gap-2.5 transition-all duration-150 cursor-pointer shadow-xs focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#DC2626]/30"
          >
            <LogOut size={18} className="text-[#DC2626] stroke-[2.2] shrink-0" aria-hidden="true" />
            <span>Log out</span>
          </button>
        </div>

      </div>

      {/* 
        ===================================================================
        LOGOUT CONFIRMATION MODAL
        - Simple, uncluttered confirmation
        - Title: "Log out?"
        - Subtitle: "Are you sure you want to log out?"
        - Buttons: Cancel, Log out
        ===================================================================
      */}
      <AnimatePresence>
        {showLogoutConfirm && (
          <div
            className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-[#031B2B]/60 backdrop-blur-xs"
            role="dialog"
            aria-modal="true"
            aria-labelledby="logout-dialog-title"
            aria-describedby="logout-dialog-desc"
            id="orca-logout-confirm-dialog"
          >
            {/* Backdrop click to cancel */}
            <div
              className="absolute inset-0"
              onClick={() => setShowLogoutConfirm(false)}
              aria-hidden="true"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="relative w-full max-w-[340px] bg-white rounded-2xl sm:rounded-3xl p-6 shadow-2xl z-10 border border-[#062A43]/10 text-center"
            >
              {/* Close icon */}
              <button
                type="button"
                onClick={() => setShowLogoutConfirm(false)}
                className="absolute top-4 right-4 w-9 h-9 rounded-full bg-[#062A43]/5 hover:bg-[#062A43]/10 text-[#062A43] flex items-center justify-center cursor-pointer transition-colors focus:outline-hidden"
                aria-label="Cancel and close dialog"
              >
                <X size={18} />
              </button>

              <div className="w-12 h-12 rounded-full bg-[#FEECEC] text-[#DC2626] flex items-center justify-center mx-auto mb-3.5">
                <LogOut size={22} className="stroke-[2.2]" />
              </div>

              <h2
                id="logout-dialog-title"
                className="font-ui font-bold text-[20px] text-[#062A43] leading-tight"
              >
                Log out?
              </h2>
              <p
                id="logout-dialog-desc"
                className="font-ui text-[14px] text-[#5A7184] leading-relaxed mt-1.5 mb-6"
              >
                Are you sure you want to log out?
              </p>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  id="orca-logout-cancel-btn"
                  onClick={() => setShowLogoutConfirm(false)}
                  className="flex-1 h-[46px] rounded-xl bg-white border border-[#D0DFEB] text-[#062A43] hover:bg-[#F7FAFC] font-ui font-medium text-[14.5px] transition-colors cursor-pointer active:scale-98 focus:outline-hidden"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  id="orca-logout-confirm-btn"
                  onClick={handleConfirmLogout}
                  className="flex-1 h-[46px] rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] text-white font-ui font-semibold text-[14.5px] transition-colors shadow-xs cursor-pointer active:scale-98 focus:outline-hidden"
                >
                  Log out
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 
        ===================================================================
        BOTTOM NAVIGATION
        - 5-item navigation (Home, Map, Ask, Alerts, Profile)
        - Profile tab is active
        ===================================================================
      */}
      <OrcaBottomNav
        activeTab="profile"
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};

export default ProfilePage;

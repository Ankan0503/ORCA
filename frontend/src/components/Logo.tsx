import React, { useState } from 'react';

interface LogoProps {
  logoSrc: string;
}

export const Logo: React.FC<LogoProps> = ({ logoSrc }) => {
  const [loadFailed, setLoadFailed] = useState(false);

  return (
    <div className="flex items-center select-none" id="orca-logo-container">
      {/* ORCA Logo - Clean, unbordered and unboxed */}
      {!loadFailed ? (
        <img
          src={logoSrc}
          alt=""
          id="orca-brand-logo"
          className="h-8 sm:h-9 md:h-10 w-auto max-w-[130px] sm:max-w-[155px] object-contain cursor-pointer transition-opacity hover:opacity-90"
          onError={() => setLoadFailed(true)}
        />
      ) : (
        /* Inline SVG Fallback representing the transparent ORCA symbol and wordmark */
        <svg
          viewBox="0 0 140 36"
          className="h-8 sm:h-9 md:h-10 w-auto cursor-pointer"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="ORCA"
          role="img"
        >
          <g>
            <path
              d="M4 27C10 27 15 24 19 19C22.5 14.5 25 7 26 3C23.5 9 18.5 13 13 14C8 15 4 19 4 27Z"
              fill="#062A43"
            />
            <path
              d="M11 27C15 27 18.5 24.5 21 21C22 19.5 23 17 23.5 15C20.5 17 17 18.5 13 19.5C9.5 20.5 7.5 23.5 7.5 27H11Z"
              fill="#1677A8"
            />
          </g>
          <text
            x="36"
            y="24"
            fontFamily="'DM Sans', -apple-system, sans-serif"
            fontSize="20"
            fontWeight="700"
            letterSpacing="0.16em"
            fill="#062A43"
          >
            ORCA
          </text>
          <circle cx="125" cy="19" r="2" fill="#1677A8" />
        </svg>
      )}
    </div>
  );
};

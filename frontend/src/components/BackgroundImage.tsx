import React, { useState } from 'react';

interface BackgroundImageProps {
  mobileSrc: string;
  desktopSrc: string;
}

export const BackgroundImage: React.FC<BackgroundImageProps> = ({ mobileSrc, desktopSrc }) => {
  const [imageLoaded, setImageLoaded] = useState(false);

  return (
    <div
      className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none select-none z-0 bg-[#F6F3ED]"
      aria-hidden="true"
      id="orca-hero-background-container"
    >
      {/* 
        Responsive Cinematic Photography:
        Native HTML5 <picture> media queries guarantee that the browser evaluates
        screen width before initiating network requests:
        - Mobile screens (< 1024px) download strictly mobileSrc (/assets/landing/orca_landing_background.avif)
        - Desktop screens (>= 1024px) download strictly desktopSrc (/assets/landing/orca_desktop_hero.avif)
        Neither device downloads the other asset, eliminating lag and conserving mobile bandwidth.
      */}
      <picture className="w-full h-full block">
        <source
          media="(min-width: 1024px)"
          srcSet={desktopSrc}
          type="image/avif"
        />
        <source
          media="(max-width: 1023px)"
          srcSet={mobileSrc}
          type="image/avif"
        />
        <img
          src={mobileSrc}
          alt=""
          className={`w-full h-full object-cover object-center lg:object-cover lg:object-right transition-opacity duration-700 ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          loading="eager"
          decoding="async"
          onLoad={() => setImageLoaded(true)}
        />
      </picture>

      {/* 
        Desktop Left Editorial Scrim:
        Gentle neutral gradient across the left 48% where the headline and navigation sit,
        ensuring optimal contrast on desktop while keeping the right side photograph bright.
      */}
      <div 
        className="hidden lg:block absolute inset-y-0 left-0 w-1/2 pointer-events-none"
        style={{
          background: 'linear-gradient(to right, rgba(246, 243, 237, 0.75) 0%, rgba(246, 243, 237, 0.35) 60%, transparent 100%)',
        }}
      />

      {/* 
        Ultra-Minimal Top Gradient on Mobile:
        Soft fade strictly at the top where the headline sits,
        leaving the photograph bright, vibrant, and clearly visible without any heavy filter.
      */}
      <div 
        className="absolute inset-x-0 top-0 h-48 pointer-events-none lg:hidden"
        style={{
          background: 'linear-gradient(to bottom, rgba(246, 243, 237, 0.45) 0%, rgba(246, 243, 237, 0.12) 50%, transparent 100%)',
        }}
      />

      {/* 
        Subtle Mobile Bottom Scrim:
        Soft fade at the bottom edge to anchor the bottom button and footer with high contrast.
      */}
      <div 
        className="absolute inset-x-0 bottom-0 h-36 pointer-events-none lg:hidden"
        style={{
          background: 'linear-gradient(to top, rgba(3, 27, 43, 0.45) 0%, rgba(3, 27, 43, 0.15) 50%, transparent 100%)',
        }}
      />
    </div>
  );
};

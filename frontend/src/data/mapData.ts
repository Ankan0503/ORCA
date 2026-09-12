export interface MapFilter {
  id: 'fishing' | 'safety' | 'pfz' | 'restrictions';
  label: string;
  icon: string;
}

/*
 * The map's fishing zones are no longer defined here. They come from INCOIS's
 * daily Potential Fishing Zone advisory, fetched at runtime by the backend and
 * drawn by OrcaLeafletMap. The old MAP_ZONES_CONFIG / MapZone / HARBOUR
 * constants were invented demo data and have been removed so nothing on the map
 * can be mistaken for a real observation.
 */

export interface MapTranslations {
  locationName: string;
  youAreHere: string;
  myLocation: string;
  updatedMinsAgo: string;
  offlineMode: string;
  openFullMap: string;
  filters: {
    fishing: string;
    safety: string;
    pfz: string;
    restrictions: string;
  };
  legend: {
    best: string;
    good: string;
    avoid: string;
    restricted: string;
  };
  /**
   * The legend as it is actually drawn.
   *
   * `legend` above describes best/good/avoid/restricted, which the map stopped
   * showing when the invented demo zones were removed. These are the rows the
   * component renders now, and they lived in a hardcoded array inside it — so
   * the legend stayed English in every language while the table around it
   * translated correctly.
   */
  legendItems: {
    key: string;
    incoisFishingZone: string;
    pfzAdvisoryLine: string;
    thunderstorm: string;
    heavyRain: string;
    lightRain: string;
    currentFaster: string;
    currentNotTrusted: string;
    indiaEez: string;
    internationalBorder: string;
    protectedArea: string;
    copernicusPfz: string;
    youAreHere: string;
    allLayersOff: string;
  };
  /** Strings that were written directly into the map's components. */
  ui: {
    checkingWaters: string;
    fishingBanInForce: string;
    insideProtectedArea: string;
    cautionMarginNote: string;
    routeHere: string;
    addToTrip: string;
    tapToPlanRoute: string;
    zoomIn: string;
    zoomOut: string;
    centreOnMyLocation: string;
    mapNavigationControls: string;
    mapLayers: string;
    mapHeader: string;
    goBackHome: string;
    mapKey: string;
    bestFishingAreaRecommendation: string;
    navigateToFindFish: string;
    closeRoute: string;
    guideMe: string;
    closeSteering: string;
    steeringGuidance: string;
    steering: string;
    courseToSteer: string;
    compassRefused: string;
    turnCompassOn: string;
    yourTrip: string;
    closeTripPlanner: string;
    tripAcrossGrounds: string;
    tapZoneAndChoose: string;
    backToStart: string;
    countPassageHome: string;
    planningEachLeg: string;
  };
  bestCard: {
    title: string;
    distance: string;
    chance: string;
    safety: string;
    viewDetails: string;
  };
  routeLabel: string;
  restrictedWarning: string;
  avoidWarning: string;
  safeToGo: string;
  goodFishing: string;
  fishingNotAllowed: string;
}

export const MAP_TRANSLATIONS: Record<string, MapTranslations> = {
  en: {
    locationName: 'Digha, West Bengal',
    youAreHere: 'You are here',
    myLocation: 'My location',
    updatedMinsAgo: 'Updated 12 mins ago',
    offlineMode: 'Offline • Cached map ready',
    openFullMap: 'Open full map',
    filters: {
      fishing: 'Fishing',
      safety: 'Safety',
      pfz: 'PFZ',
      restrictions: 'Restrictions',
    },
    legend: {
      best: 'Best fishing',
      good: 'Good fishing',
      avoid: 'Avoid',
      restricted: 'Restricted',
    },
    legendItems: {
      key: 'Key',
      incoisFishingZone: 'INCOIS fishing zone',
      pfzAdvisoryLine: 'PFZ advisory line',
      thunderstorm: 'Thunderstorm — lightning',
      heavyRain: 'Heavy rain',
      lightRain: 'Light rain',
      currentFaster: 'Current (longer = faster)',
      currentNotTrusted: 'Current not trusted here',
      indiaEez: 'India EEZ',
      internationalBorder: 'International border',
      protectedArea: 'Protected area',
      copernicusPfz: 'Satellite PFZ (cloud-bypass)',
      youAreHere: 'You are here',
      allLayersOff: 'All layers are switched off — tap a chip above to bring one back.',
    },
    ui: {
      checkingWaters: 'Checking waters…',
      fishingBanInForce: 'Fishing ban in force',
      insideProtectedArea: 'Inside a protected area',
      cautionMarginNote: 'ORCA caution margin, not a legal limit',
      routeHere: 'Route here →',
      addToTrip: 'Add to trip',
      tapToPlanRoute: 'Tap to plan the route',
      zoomIn: 'Zoom in',
      zoomOut: 'Zoom out',
      centreOnMyLocation: 'Centre on my location',
      mapNavigationControls: 'Map navigation controls',
      mapLayers: 'Map layers',
      mapHeader: 'Map header',
      goBackHome: 'Go back to Home',
      mapKey: 'Map key',
      bestFishingAreaRecommendation: 'Best fishing area recommendation',
      navigateToFindFish: 'Navigate to Find Fish details',
      closeRoute: 'Close route',
      guideMe: 'Guide me →',
      closeSteering: 'Close steering guidance',
      steeringGuidance: 'Steering guidance',
      steering: 'Steering',
      courseToSteer: 'Course to steer',
      compassRefused: 'Compass access was refused. Steer',
      turnCompassOn: 'Turn the compass on',
      yourTrip: 'Your trip',
      closeTripPlanner: 'Close the trip planner',
      tripAcrossGrounds: 'Trip across several fishing grounds',
      tapZoneAndChoose: 'Tap a fishing zone on the map and choose',
      backToStart: 'Back to where you started',
      countPassageHome: 'Count the passage home — it is usually the longest leg',
      planningEachLeg: 'Planning each leg around the weather…',
    },
    bestCard: {
      title: 'Best fishing area',
      distance: '12 km offshore',
      chance: 'Good fishing chance',
      safety: 'Safe to go',
      viewDetails: 'View details',
    },
    routeLabel: 'Recommended route • 12 km',
    restrictedWarning: 'Restricted area',
    avoidWarning: 'Avoid area • Storm risk',
    safeToGo: 'Safe to go',
    goodFishing: 'Good fishing',
    fishingNotAllowed: 'Fishing is not allowed here.',
  },
  bn: {
    locationName: 'দীঘা, পশ্চিমবঙ্গ',
    youAreHere: 'আপনি এখানে আছেন',
    myLocation: 'আমার অবস্থান',
    updatedMinsAgo: '১২ মিনিট আগে আপডেট হয়েছে',
    offlineMode: 'অফলাইন • সংরক্ষিত মানচিত্র প্রস্তুত',
    openFullMap: 'সম্পূর্ণ মানচিত্র দেখুন',
    filters: {
      fishing: 'মাছ শিকার',
      safety: 'নিরাপত্তা',
      pfz: 'PFZ (সম্ভাব্য স্থান)',
      restrictions: 'নিষিদ্ধ এলাকা',
    },
    legend: {
      best: 'সেরা স্থান',
      good: 'ভালো স্থান',
      avoid: 'যাবেন না',
      restricted: 'নিষিদ্ধ',
    },
    legendItems: {
      key: 'মানচিত্রের চাবিকাঠি, কিংবদন্তি',
      incoisFishingZone: 'মৎস্য-আবাস',
      pfzAdvisoryLine: 'পরামর্শমূলক লাইন',
      thunderstorm: 'বজ্রপাত',
      heavyRain: 'ভারী বৃষ্টি',
      lightRain: 'হালকা বৃষ্টি',
      currentFaster: 'জলের প্রবাহ, একটি দীর্ঘ তীর মানে দ্রুত',
      currentNotTrusted: 'জলপ্রবাহ এখানে অবিশ্বস্ত।',
      indiaEez: 'ভারতের এক্সক্লুসিভ ইকোনমিক জোন',
      internationalBorder: 'আন্তর্জাতিক সীমানা',
      protectedArea: 'সংরক্ষিত এলাকা।',
      copernicusPfz: 'স্যাটেলাইট পিএফজেড (মেঘ-বাইপাস)',
      youAreHere: 'আপনি এখানে আছেন।',
      allLayersOff: 'সমস্ত স্তর বন্ধ থাকে - একটি ফিরিয়ে আনার জন্য উপরে একটি চিপে ট্যাপ করুন।',
    },
    ui: {
      checkingWaters: 'জল পরীক্ষা করা হচ্ছে...',
      fishingBanInForce: 'মাছ ধরার উপর নিষেধাজ্ঞা কার্যকর',
      insideProtectedArea: 'সুরক্ষিত এলাকায়',
      cautionMarginNote: 'ORCA সতর্কতা ব্যবধান, কোনও আইনি সীমা নয়',
      routeHere: 'পরিকল্পনা করুন এখানে একটি পথ →',
      addToTrip: 'এটি আমার ভ্রমণে যোগ করুন।',
      tapToPlanRoute: 'পথ পরিকল্পনা করার জন্য ট্যাপ করুন।',
      zoomIn: 'জুম ইন',
      zoomOut: 'জুম আউট',
      centreOnMyLocation: 'আমার অবস্থানের কেন্দ্রে কেন্দ্র করুন।',
      mapNavigationControls: 'মানচিত্র নড়াচড়া নিয়ন্ত্রণ করে',
      mapLayers: 'মানচিত্রের স্তর',
      mapHeader: 'মানচিত্রের শিরোনাম',
      goBackHome: 'হোম-এ ফিরে যান।',
      mapKey: 'মানচিত্রের চাবিকাঠি',
      bestFishingAreaRecommendation: 'সেরা মাছ ধরার স্থানের সুপারিশ।',
      navigateToFindFish: 'মাছের খোঁজের বিস্তারিত তথ্যয় যাওয়া যায়।',
      closeRoute: 'নিকটবর্তী পথ',
      guideMe: 'আমাকে সেখানে পরিচালিত করুন, →',
      closeSteering: 'ক্লোজ স্টিয়ারিং গাইডেন্স',
      steeringGuidance: 'চালনা নির্দেশনা।',
      steering: 'নৌকা চালানো',
      courseToSteer: 'চালনা',
      compassRefused: 'কম্পাস ব্যবহার করার অনুমতি প্রত্যাখ্যান করা হয়েছিল। গরু',
      turnCompassOn: 'চৌম্বক সুঁচটি চালু করুন।',
      yourTrip: 'আপনার পরিকল্পিত ভ্রমণ',
      closeTripPlanner: 'ট্রিপ প্ল্যানারটি বন্ধ করে দিন।',
      tripAcrossGrounds: 'একাধিক মাছ ধরার জায়গায় যাওয়া',
      tapZoneAndChoose: 'মানচিত্রের একটি মাছ ধরার অঞ্চল নির্বাচন করুন এবং নির্বাচন করুন',
      backToStart: 'আপনি যেখানে থেকে শুরু করেছিলেন সেখানে ফিরে যান।',
      countPassageHome: 'বাড়ি ফেরার পথে কতগুলি গন্তব্যস্থল গণনা করুন - এটি সাধারণত দীর্ঘতম পথ।',
      planningEachLeg: 'প্রতিটি পর্যায়ের পরিকল্পনা আবহাওয়ার উপর ভিত্তি করে...',
    },
    bestCard: {
      title: 'সেরা মাছ ধরার এলাকা',
      distance: 'উপকূল থেকে ১২ কিমি',
      chance: 'বেশি মাছ পাওয়ার সম্ভাবনা',
      safety: 'যাওয়ার জন্য নিরাপদ',
      viewDetails: 'বিস্তারিত দেখুন',
    },
    routeLabel: 'প্রস্তাবিত রুট • ১২ কিমি',
    restrictedWarning: 'নিষিদ্ধ এলাকা',
    avoidWarning: 'ঝুঁকিপূর্ণ এলাকা • ঝড়ের আশঙ্কা',
    safeToGo: 'যাওয়া নিরাপদ',
    goodFishing: 'ভালো মাছের সম্ভাবনা',
    fishingNotAllowed: 'এখানে মাছ ধরা সম্পূর্ণ নিষিদ্ধ।',
  },
  ta: {
    locationName: 'திகா, மேற்கு வங்காளம்',
    youAreHere: 'நீங்கள் இங்கு உள்ளீர்கள்',
    myLocation: 'எனது இருப்பிடம்',
    updatedMinsAgo: '12 நிமிடங்களுக்கு முன் புதுப்பிக்கப்பட்டது',
    offlineMode: 'ஆஃப்லைன் • மேப் தயார்',
    openFullMap: 'முழு வரைபடத்தைத் திறக்க',
    filters: {
      fishing: 'மீன்பிடி',
      safety: 'பாதுகாப்பு',
      pfz: 'PFZ',
      restrictions: 'தடைசெய்யப்பட்டவை',
    },
    legend: {
      best: 'சிறந்த பகுதி',
      good: 'நல்ல பகுதி',
      avoid: 'தவிர்க்கவும்',
      restricted: 'தடைசெய்யப்பட்டது',
    },
    legendItems: {
      key: 'வரைபடக் குறிப்பு, புராணக்கதை',
      incoisFishingZone: 'மீன் பிடித்துறை',
      pfzAdvisoryLine: 'ஆலோசனை வரி',
      thunderstorm: 'மின்னலடிப்பு',
      heavyRain: 'கனமழை',
      lightRain: 'லேசான மழை',
      currentFaster: 'நீரோட்டக் குறியீடு, நீண்ட அம்பு வேகத்தைக் குறிக்கிறது.',
      currentNotTrusted: 'நீர் ஓட்டம் இங்கு நம்பத்தகாதது.',
      indiaEez: 'இந்தியாவின் பிரத்யேக பொருளாதார மண்டலம்',
      internationalBorder: 'சர்வதேச எல்லை',
      protectedArea: 'பாதுகாக்கப்பட்ட பகுதி.',
      copernicusPfz: 'செயற்கைக்கோள் PFZ (மேக-பைபாஸ்)',
      youAreHere: 'நீங்கள் இங்கே இருக்கிறீர்கள்',
      allLayersOff: 'அனைத்து அடுக்குகளும் அணைக்கப்பட்டுள்ளன - ஒன்றை மீண்டும் இயக்க மேலே உள்ள ஒரு சிப்பைத் தட்டவும்.',
    },
    ui: {
      checkingWaters: 'நீர்நிலைகளைச் சரிபார்த்தல்...',
      fishingBanInForce: 'மீன்பிடித் தடைக் காலம்',
      insideProtectedArea: 'பாதுகாக்கப்பட்ட பகுதியில்',
      cautionMarginNote: 'ORCA எச்சரிக்கை வரம்பு, சட்ட வரம்பு இல்லை',
      routeHere: 'இங்கே → செல்ல ஒரு பாதையைத் திட்டமிடுங்கள்',
      addToTrip: 'இதை எனது பயணத்தில் சேர்க்கிறேன்.',
      tapToPlanRoute: 'வழித்தடத்தைத் திட்டமிடத் தொடங்குங்கள்.',
      zoomIn: 'நெருக்கமான பார்வை',
      zoomOut: 'வெளியே பார்வை',
      centreOnMyLocation: 'எனது இருப்பிடத்தின் மையத்தில் மையப்படுத்தப்பட்டுள்ளது',
      mapNavigationControls: 'வரைபட வழிசெலுத்தல் கட்டுப்பாடுகள்',
      mapLayers: 'வரைபட அடுக்குகள்',
      mapHeader: 'வரைபடத் தலைப்பு',
      goBackHome: 'வலைத்தளத்திற்குத் திரும்பு.',
      mapKey: 'வரைபடக் குறிப்பு',
      bestFishingAreaRecommendation: 'சிறந்த மீன்பிடிப் பகுதி பரிந்துரை',
      navigateToFindFish: 'மீன் விவரங்களைக் கண்டறியவும்.',
      closeRoute: 'தடைசெய்யப்பட்ட பாதை',
      guideMe: 'அங்கு → செல்ல வழிகாட்டவும்.',
      closeSteering: 'திசை அறிவுறுத்தல் நிறுத்தப்படுகிறது.',
      steeringGuidance: 'வழிநடத்தும் வழிகாட்டுதல்.',
      steering: 'படகோட்டம்',
      courseToSteer: 'திசைக் கருவி',
      compassRefused: 'திசைகாட்டி மூலம் அணுகல் மறுக்கப்பட்டது. குதிரை',
      turnCompassOn: 'திசைகாட்டியை இயக்கவும்.',
      yourTrip: 'திட்டமிட்ட பயணம்.',
      closeTripPlanner: 'பயணத் திட்டத்தைச் சேமிக்கவும்.',
      tripAcrossGrounds: 'பல மீன்பிடி இடங்களுக்குச் செல்வது',
      tapZoneAndChoose: 'வரைபடத்தில் மீன்பிடி மண்டலத்தைத் தட்டித் தேர்ந்தெடுக்கவும்',
      backToStart: 'நீங்கள் தொடங்கிய இடத்திற்குத் திரும்பு.',
      countPassageHome: 'வீட்டுக்கு செல்லும் வழியில் உள்ள நிறுத்தங்களை எண்ணிப் பாருங்கள் - இது பொதுவாக மிக நீண்ட தூரம் பயணிக்க வேண்டியிருக்கும்',
      planningEachLeg: 'ஒவ்வொரு கட்டத்திலும் வானிலையைக் கருத்தில் கொண்டு திட்டமிடுகிறோம்...',
    },
    bestCard: {
      title: 'சிறந்த மீன்பிடி பகுதி',
      distance: '12 கி.மீ ஆழ்கடல்',
      chance: 'அதிக மீன் வாய்ப்பு',
      safety: 'செல்ல பாதுகாப்பானது',
      viewDetails: 'விவரம் காண்க',
    },
    routeLabel: 'பரிந்துரைக்கப்பட்ட வழி • 12 கி.மீ',
    restrictedWarning: 'தடைசெய்யப்பட்ட பகுதி',
    avoidWarning: 'தவிர்க்க வேண்டிய பகுதி • புயல் அபாயம்',
    safeToGo: 'செல்ல பாதுகாப்பானது',
    goodFishing: 'நல்ல மீன்பிடி',
    fishingNotAllowed: 'இங்கு மீன்பிடிக்க அனுமதி இல்லை.',
  },
  te: {
    locationName: 'దిఘా, పశ్చిమ బెంగాల్',
    youAreHere: 'మీరు ఇక్కడ ఉన్నారు',
    myLocation: 'నా స్థానం',
    updatedMinsAgo: '12 నిమిషాల క్రితం నవీకరించబడింది',
    offlineMode: 'ఆఫ్‌లైన్ • మ్యాప్ సిద్ధంగా ఉంది',
    openFullMap: 'పూర్తి మ్యాప్ చూడండి',
    filters: {
      fishing: 'చేపల వేట',
      safety: 'భద్రత',
      pfz: 'PFZ',
      restrictions: 'నిషేధిత ప్రాంతాలు',
    },
    legend: {
      best: 'ఉత్తమ ప్రాంతం',
      good: 'మంచి ప్రాంతం',
      avoid: 'వెళ్లవద్దు',
      restricted: 'నిషేధించబడింది',
    },
    legendItems: {
      key: 'మ్యాప్ కీ, పురాణం',
      incoisFishingZone: 'చేపల వేట ప్రాంతం',
      pfzAdvisoryLine: 'సలహా రేఖ',
      thunderstorm: 'తుపాను',
      heavyRain: 'భారీ వర్షం',
      lightRain: 'తేలికపాటి వర్షం',
      currentFaster: 'నీటి ప్రవాహం, పొడవైన బాణం అంటే వేగవంతమైనది అని అర్థం.',
      currentNotTrusted: 'ఇక్కడ నీటి ప్రవాహం నమ్మదగినది కాదు.',
      indiaEez: 'భారతదేశం యొక్క ప్రత్యేక ఆర్థిక మండలం',
      internationalBorder: 'అంతర్జాతీయ సరిహద్దు',
      protectedArea: 'రక్షిత ప్రాంతం.',
      copernicusPfz: 'శాటిలైట్ PFZ (క్లౌడ్-బైపాస్)',
      youAreHere: 'మీరు ఇక్కడ ఉన్నారు',
      allLayersOff: 'అన్ని పొరలు స్విచ్ ఆఫ్ చేయబడి ఉంటాయి-ఒకటి తిరిగి తెచ్చుకోవడానికి పైన ఉన్న ఒక చిప్‌ను నొక్కండి.',
    },
    ui: {
      checkingWaters: 'జలాలను పరిశీలిస్తున్నాను...',
      fishingBanInForce: 'చేపల వేట నిషేధం అమలులో ఉంది',
      insideProtectedArea: 'రక్షిత ప్రాంతంలో',
      cautionMarginNote: 'ORCA జాగ్రత్త మార్జిన్, చట్టబద్ధమైన పరిమితి కాదు',
      routeHere: 'ఇక్కడకు వెళ్ళే మార్గాన్ని ప్రణాళిక చేయండి',
      addToTrip: 'దీన్ని నా ప్రయాణంలో చేర్చండి.',
      tapToPlanRoute: 'మార్గం ప్రణాళిక చేస్కోండి',
      zoomIn: 'జూమ్ ఇన్',
      zoomOut: 'జూమ్ అవుట్',
      centreOnMyLocation: 'నా స్థానం మీద కేంద్రీకృతమై ఉంది',
      mapNavigationControls: 'మ్యాప్ నావిగేషన్',
      mapLayers: 'పటముల పొరలు',
      mapHeader: 'మ్యాప్ శీర్షిక',
      goBackHome: 'హోమ్ పేజీకి తిరిగి వెళ్ళు.',
      mapKey: 'మ్యాప్ కీ',
      bestFishingAreaRecommendation: 'ఉత్తమ చేపలు పట్టే ప్రాంతం సిఫార్సు',
      navigateToFindFish: 'చేపలను వెతకడానికి వెళ్ళండి.',
      closeRoute: 'మూస దారి',
      guideMe: 'నన్ను అక్కడికి దారి చూపండి.',
      closeSteering: 'దగ్గరి మార్గదర్శకత్వం',
      steeringGuidance: 'స్టీరింగ్ మార్గదర్శకత్వం.',
      steering: 'పడవ నడిపించడం',
      courseToSteer: 'దిశానిర్దేశం చేసే వాహనం',
      compassRefused: 'దిక్సూచి ద్వారా ప్రవేశం నిరాకరించబడింది. గుర్రం',
      turnCompassOn: 'దిక్సూచిని ఆన్ చేయండి',
      yourTrip: 'మీ ప్రణాళిక ప్రకారం',
      closeTripPlanner: 'ట్రిప్ ప్లానర్ మూసివేయండి.',
      tripAcrossGrounds: 'అనేక చేపల వేట ప్రదేశాల గుండా ప్రయాణించడం',
      tapZoneAndChoose: 'మ్యాప్ లో ఫిషింగ్ జోన్‌పై నొక్కి ఎంచుకోండి',
      backToStart: 'మీరు మొదలు పెట్టిన చోటికి తిరిగి వెళ్ళు',
      countPassageHome: 'ఇంటికి వెళ్ళేటప్పుడు పాసేజ్‌ను లెక్కించుకోండి-ఇది సాధారణంగా అతి పొడవైన దశ.',
      planningEachLeg: 'ప్రతి దశను వాతావరణ పరిస్థితుల ఆధారంగా ప్రణాళిక చేస్తున్నారు...',
    },
    bestCard: {
      title: 'ఉత్తమ వేట ప్రాంతం',
      distance: 'తీరానికి 12 కి.మీ',
      chance: 'చేపలు దొరికే అవకాశం ఎక్కువ',
      safety: 'సురక్షితమైనది',
      viewDetails: 'వివరాలు చూడండి',
    },
    routeLabel: 'సిఫార్సు చేయబడిన మార్గం • 12 కి.మీ',
    restrictedWarning: 'నిషేధిత ప్రాంతం',
    avoidWarning: 'ప్రమాదకర ప్రాంతం • తుఫాను ప్రమాదం',
    safeToGo: 'వెళ్లడం సురక్షితం',
    goodFishing: 'మంచి వేట',
    fishingNotAllowed: 'ఇక్కడ చేపలు పట్టడం అనుమతించబడదు.',
  },
  hi: {
    locationName: 'दीघा, पश्चिम बंगाल',
    youAreHere: 'आप यहाँ हैं',
    myLocation: 'मेरा स्थान',
    updatedMinsAgo: '12 मिनट पहले अपडेट हुआ',
    offlineMode: 'ऑफ़लाइन • सहेजा गया मैप तैयार है',
    openFullMap: 'पूरा नक्शा देखें',
    filters: {
      fishing: 'मछली पकड़ना',
      safety: 'सुरक्षा',
      pfz: 'PFZ',
      restrictions: 'प्रतिबंधित क्षेत्र',
    },
    legend: {
      best: 'सर्वोत्तम क्षेत्र',
      good: 'अच्छा क्षेत्र',
      avoid: 'बचें',
      restricted: 'प्रतिबंधित',
    },
    legendItems: {
      key: 'मानचित्र कुंजी, आख्यान',
      incoisFishingZone: 'क्षेत्र',
      pfzAdvisoryLine: 'सलाहकार रेखा',
      thunderstorm: 'आँधी',
      heavyRain: 'भारी वर्षा',
      lightRain: 'बूंदाबांदी',
      currentFaster: 'जल धारा, एक लंबे तीर का मतलब तेज़ी है',
      currentNotTrusted: 'यहाँ जल प्रवाह अविश्वसनीय है',
      indiaEez: 'भारत का विशेष आर्थिक क्षेत्र',
      internationalBorder: 'अंतर्राष्ट्रीय सीमा',
      protectedArea: 'संरक्षित क्षेत्र।',
      copernicusPfz: 'सैटेलाइट PFZ (क्लाउड-बायपास)',
      youAreHere: 'आप यहाँ हैं।',
      allLayersOff: 'सभी परतें बंद कर दी गई हैं - एक परत वापस लाने के लिए ऊपर की चिप पर टैप करें।',
    },
    ui: {
      checkingWaters: 'पानी की जाँच कर रहा हूँ...',
      fishingBanInForce: 'मछली पकड़ने पर प्रतिबंध जारी है।',
      insideProtectedArea: 'संरक्षित क्षेत्र के अंदर',
      cautionMarginNote: '@0@@ सावधानी का अंतराल, कानूनी सीमा नहीं',
      routeHere: 'यहाँ तक एक मार्ग की योजना बनाएँ →',
      addToTrip: 'इसे मेरी यात्रा में जोड़ दीजिए।',
      tapToPlanRoute: 'मार्ग की योजना बनाने के लिए टैप करें।',
      zoomIn: 'ज़ूम इन',
      zoomOut: 'बाहर देखना',
      centreOnMyLocation: 'मेरे स्थान पर केंद्र करें',
      mapNavigationControls: 'मानचित्र नेविगेशन',
      mapLayers: 'मानचित्र परतें',
      mapHeader: 'मानचित्र शीर्षक',
      goBackHome: 'गृह पृष्ठ पर वापस जाएँ।',
      mapKey: 'मानचित्र कुंजी',
      bestFishingAreaRecommendation: 'सबसे अच्छा मछली पकड़ने का क्षेत्र सुझाव',
      navigateToFindFish: 'मछली खोजने के विवरण पर जाएँ।',
      closeRoute: 'निकट मार्ग',
      guideMe: 'मुझे वहाँ ले चलिए →',
      closeSteering: 'निकट मार्गदर्शन',
      steeringGuidance: 'संचालन मार्गदर्शन।',
      steering: 'नाव चलाना',
      courseToSteer: 'स्टीयरिंग',
      compassRefused: 'कंपास से अभिगम करने से मना कर दिया गया। घोड़ा',
      turnCompassOn: 'कम्पास चालू करें।',
      yourTrip: 'आपकी नियोजित यात्रा',
      closeTripPlanner: 'यात्रा योजना बंद कर दीजिए।',
      tripAcrossGrounds: 'कई मछली पकड़ने के मैदानों पर जाना',
      tapZoneAndChoose: 'नक्शे पर मछली पकड़ने वाले क्षेत्र पर टैप करें और चुनें',
      backToStart: 'जहाँ से आरंभ किया था, वहीं वापस',
      countPassageHome: 'घर पहुँचने के लिए गिने - यह आम तौर पर सबसे लंबा चरण होता है',
      planningEachLeg: 'प्रत्येक चरण को मौसम के अनुसार योजना बनाना...',
    },
    bestCard: {
      title: 'सर्वोत्तम मछली क्षेत्र',
      distance: 'तट से 12 किमी',
      chance: 'अच्छी मछली मिलने की संभावना',
      safety: 'जाना सुरक्षित है',
      viewDetails: 'विवरण देखें',
    },
    routeLabel: 'सुझाया गया मार्ग • 12 किमी',
    restrictedWarning: 'प्रतिबंधित क्षेत्र',
    avoidWarning: 'बचने योग्य क्षेत्र • तूफ़ान का ख़तरा',
    safeToGo: 'जाना सुरक्षित है',
    goodFishing: 'मछली पकड़ने के लिए बढ़िया',
    fishingNotAllowed: 'यहाँ मछली पकड़ने की अनुमति नहीं है।',
  },
  ml: {
    locationName: 'ദിഘ, പശ്ചിമ ബംഗാൾ',
    youAreHere: 'നിങ്ങൾ ഇവിടെയാണ്',
    myLocation: 'എന്റെ സ്ഥാനം',
    updatedMinsAgo: '12 മിനിറ്റ് മുൻപ് അപ്‌ഡേറ്റ് ചെയ്തു',
    offlineMode: 'ഓഫ്‌ലൈൻ • മാപ്പ് തയ്യാറാണ്',
    openFullMap: 'പൂർണ്ണ ഭൂപടം കാണുക',
    filters: {
      fishing: 'മത്സ്യബന്ധനം',
      safety: 'സുരക്ഷ',
      pfz: 'PFZ',
      restrictions: 'വിലക്കുള്ള മേഖല',
    },
    legend: {
      best: 'മികച്ച മേഖല',
      good: 'നല്ല മേഖല',
      avoid: 'ഒഴിവാക്കുക',
      restricted: 'വിലക്കുള്ളത്',
    },
    legendItems: {
      key: 'ഭൂപടത്തിലെ കീ, ആലേഖനം',
      incoisFishingZone: 'മത്സ്യബന്ധന മേഖല',
      pfzAdvisoryLine: 'നിര്ദ്ദേശം',
      thunderstorm: 'മിന്നൽ-തീപ്പിടിത്തം',
      heavyRain: 'കനത്ത മഴ',
      lightRain: 'നേരിയ മഴ',
      currentFaster: 'ജലപ്രവാഹം, ഒരു നീണ്ട അമ്പ് എന്നാൽ വേഗം എന്നാണ് അർത്ഥമാക്കുന്നത്',
      currentNotTrusted: 'ജലപ്രവാഹം ഇവിടെ വിശ്വസനീയമല്ല.',
      indiaEez: 'ഇന്ത്യയുടെ പ്രത്യേക സാമ്പത്തിക മേഖല',
      internationalBorder: 'അന്താരാഷ്‌ട്ര അതിർത്തി',
      protectedArea: 'സംരക്ഷിത പ്രദേശം.',
      copernicusPfz: 'ഉപഗ്രഹ PFZ (ക്ലൗഡ്-ബൈപാസ്)',
      youAreHere: 'താങ്കൾ ഇവിടെയാണ്',
      allLayersOff: 'എല്ലാ പാളികളും സ്വിച്ച് ഓഫ് ചെയ്തിരിക്കുന്നു - ഒരു പാളി തിരികെ കൊണ്ടുവരാൻ മുകളിലുള്ള ഒരു ചിപ്പിൽ ടാപ്പ് ചെയ്യുക.',
    },
    ui: {
      checkingWaters: 'ജലം പരിശോധിക്കുന്നു...',
      fishingBanInForce: 'മത്സ്യബന്ധന നിരോധനം നിലവിലുണ്ട്',
      insideProtectedArea: 'സംരക്ഷിത പ്രദേശത്തിനുള്ളിൽ',
      cautionMarginNote: 'ORCA മുന്നറിയിപ്പ് മാർജിൻ, നിയമപരമായ പരിധി അല്ല',
      routeHere: 'ഇവിടെയിലേക്ക് ഒരു റൂട്ട് പ്ലാൻ ചെയ്യുക.',
      addToTrip: 'ഇത് എന്‍റെ യാത്രയിൽ ചേർക്കുക.',
      tapToPlanRoute: 'റൂട്ട് ആസൂത്രണം ചെയ്യുന്നതിനായി ടാപ്പുചെയ്യുക',
      zoomIn: 'സൂം ഇന്‍',
      zoomOut: 'സൂം ഔട്ട്',
      centreOnMyLocation: 'എന്റെ സ്ഥാനത്ത് കേന്ദ്രീകരിക്കുക',
      mapNavigationControls: 'ഭൂപട നാവിഗേഷന്‍',
      mapLayers: 'ഭൂപടത്തിലെ പാളികള്‍',
      mapHeader: 'ഭൂപടത്തിന്റെ തലക്കെട്ട്',
      goBackHome: 'ഹോം പേജിലേക്ക് മടങ്ങുക.',
      mapKey: 'ഭൂപടത്തിലെ കീ',
      bestFishingAreaRecommendation: 'ഏറ്റവും നല്ല മത്സ്യബന്ധന സ്ഥലം',
      navigateToFindFish: 'മത്സ്യവിവരങ്ങൾ കണ്ടെത്തുക എന്നതിലേക്ക് നാവിഗേറ്റ് ചെയ്യുക.',
      closeRoute: 'അടുത്തുള്ള',
      guideMe: 'താങ്കളെ അവിടെ എത്തിക്കുന്നതിനുള്ള വഴിയാണ്.',
      closeSteering: 'സ്റ്റിയറിംഗ് ഗൈഡൻസ്',
      steeringGuidance: 'സ്റ്റിയറിംഗ് ഗൈഡൻസ്.',
      steering: 'ബോട്ടു് നയിക്കൽ',
      courseToSteer: 'ദിശാസൂചകം',
      compassRefused: 'കമ്പാസ് ആക്സസ് നിഷേധിക്കപ്പെട്ടു. ഓട്ടോറിക്ഷ',
      turnCompassOn: 'കമ്പസ് ഓണാക്കുക',
      yourTrip: 'താങ്കൾ ആസൂത്രണം ചെയ്ത യാത്ര',
      closeTripPlanner: 'യാത്രാ പദ്ധതി അടയ്ക്കുക.',
      tripAcrossGrounds: 'നിരവധി മത്സ്യബന്ധന സ്ഥലങ്ങൾ സന്ദർശിക്കുക',
      tapZoneAndChoose: 'ഭൂപടത്തിൽ ഒരു മത്സ്യബന്ധന മേഖല തിരഞ്ഞെടുത്ത് തിരഞ്ഞെടുക്കുക.',
      backToStart: 'താങ്കൾ ആരംഭിച്ച സ്ഥലത്തേക്ക് തിരികെ',
      countPassageHome: 'വീട്ടിലേക്ക് പോകുമ്പോള്‍ എത്ര ദൂരം സഞ്ചരിക്കുന്നുവെന്ന് കണക്കാക്കുക - ഇത് സാധാരണയായി ഏറ്റവും ദൈർഘ്യമേറിയതാണ്',
      planningEachLeg: 'ഓരോ ഘട്ടവും കാലാവസ്ഥയെ അടിസ്ഥാനമാക്കി ആസൂത്രണം ചെയ്യുക...',
    },
    bestCard: {
      title: 'മികച്ച മത്സ്യബന്ധന മേഖല',
      distance: 'തീരത്തുനിന്ന് 12 കി.മീ',
      chance: 'കൂടുതൽ മീൻ ലഭിക്കാൻ സാധ്യത',
      safety: 'പോകുന്നത് സുരക്ഷിതം',
      viewDetails: 'വിശദാംശങ്ങൾ',
    },
    routeLabel: 'നിർദ്ദേശിച്ച വഴി • 12 കി.മീ',
    restrictedWarning: 'വിലക്കുള്ള മേഖല',
    avoidWarning: 'ഒഴിവാക്കേണ്ട സ്ഥലം • കാറ്റ് സാധ്യത',
    safeToGo: 'പോകാൻ സുരക്ഷിതം',
    goodFishing: 'നല്ല മത്സ്യസാധ്യത',
    fishingNotAllowed: 'ഇവിടെ മത്സ്യബന്ധനം അനുവദനീയമല്ല.',
  },
};

export const getMapTranslations = (langCode = 'en'): MapTranslations => {
  // Hand-written table first, then the generated catalogue for the languages
  // it never covered, then English. The English fallback stays last and is
  // deliberate: a missing string should show a word the reader may not know
  // rather than nothing at all.
  return (
    MAP_TRANSLATIONS[langCode] ||
    (GENERATED_TRANSLATIONS.mapData?.[langCode] as MapTranslations | undefined) ||
    MAP_TRANSLATIONS.en
  );
};
import { GENERATED_TRANSLATIONS } from './generatedTranslations';

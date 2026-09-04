export interface MapFilter {
  id: 'fishing' | 'safety' | 'pfz' | 'restrictions';
  label: string;
  icon: string;
}

export interface MapZone {
  id: 'best-zone' | 'good-zone' | 'avoid-zone' | 'restricted-zone';
  type: 'best' | 'good' | 'avoid' | 'restricted';
  name: string;
  distance: string;
  status: string;
  statusType: 'safe' | 'caution' | 'danger' | 'restricted';
  summary: string;
  details: string;
  cx: number;
  cy: number;
  rx: number;
  ry: number;
}

export interface MapTranslations {
  locationName: string;
  youAreHere: string;
  myLocation: string;
  updatedMinsAgo: string;
  offlineMode: string;
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
  return MAP_TRANSLATIONS[langCode] || MAP_TRANSLATIONS.en;
};

export const MAP_ZONES_CONFIG: MapZone[] = [
  {
    id: 'best-zone',
    type: 'best',
    name: 'Best fishing area',
    distance: '12 km offshore',
    status: 'Safe to go • High fish activity',
    statusType: 'safe',
    summary: 'Water temp 27.5°C, high chlorophyll plankton corridor.',
    details: 'Optimal thermal oceanic front detected 12 km South-East of Digha harbour. High density of Hilsa and Indian Mackerel. Calm sea until 2 PM.',
    cx: 250,
    cy: 230,
    rx: 48,
    ry: 36,
  },
  {
    id: 'good-zone',
    type: 'good',
    name: 'Good fishing area',
    distance: '18 km offshore',
    status: 'Safe until 1:30 PM • Moderate catch',
    statusType: 'caution',
    summary: 'Water temp 28.1°C, favorable tide run.',
    details: 'Moderate school activity. Suitable for gillnetting. Return towards coast before 2 PM when southerly swell rises.',
    cx: 360,
    cy: 280,
    rx: 60,
    ry: 40,
  },
  {
    id: 'avoid-zone',
    type: 'avoid',
    name: 'Avoid area',
    distance: 'Storm-risk zone',
    status: 'High risk • Do not enter',
    statusType: 'danger',
    summary: 'Submerged shifting sandbar and squall winds >38 km/h.',
    details: 'Dangerous cross-currents over shallow sandbar. Squall winds expected after 2 PM with 2.2m wave crests. Keep at least 5 km clear.',
    cx: 380,
    cy: 90,
    rx: 50,
    ry: 32,
  },
  {
    id: 'restricted-zone',
    type: 'restricted',
    name: 'Restricted area',
    distance: 'Protected coastal zone',
    status: 'Restricted • No fishing',
    statusType: 'restricted',
    summary: 'Protected marine sanctuary & maritime navigation corridor.',
    details: 'Fishing is strictly not allowed here under coastal conservation and maritime shipping channel regulations.',
    cx: 120,
    cy: 290,
    rx: 44,
    ry: 30,
  },
];

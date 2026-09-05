export interface CardTranslation {
  title: string;
  description: string;
}

export interface AskTranslation {
  title: string;
  description: string;
  suggestion: string;
}

export interface NavTranslation {
  home: string;
  map: string;
  ask: string;
  alerts: string;
  profile: string;
}

export interface LocationTranslation {
  title: string;
  searchPlaceholder: string;
  detect: string;
  detecting: string;
  noResults: string;
  blocked: string;
  unavailable: string;
  current: string;
  searching: string;
}

export interface HomeTranslation {
  locationName: string;
  locationDetected: string;
  location: LocationTranslation;
  greetings: {
    morning: string;
    afternoon: string;
    evening: string;
  };
  fisherman: string;
  mainQuestion: string;
  cards: {
    'find-fish': CardTranslation;
    'is-it-safe': CardTranslation;
    'sea-today': CardTranslation;
    alerts: CardTranslation;
  };
  ask: AskTranslation;
  nav: NavTranslation;
}

export const HOME_TRANSLATIONS: Record<string, HomeTranslation> = {
  en: {
    locationName: 'Digha, West Bengal',
    locationDetected: 'Location detected',
    location: {
      title: 'Set your location',
      searchPlaceholder: 'Search for a harbour or town…',
      detect: 'Detect my location',
      detecting: 'Finding your location…',
      noResults: 'No places found',
      blocked: 'Location permission is blocked. Allow it, or search above.',
      unavailable: 'Could not get your location. Please search instead.',
      current: 'Current',
      searching: 'Searching…',
    },
    greetings: {
      morning: 'Good morning,',
      afternoon: 'Good afternoon,',
      evening: 'Good evening,',
    },
    fisherman: 'Fisherman',
    mainQuestion: 'What do you need today?',
    cards: {
      'find-fish': {
        title: 'Find Fish',
        description: 'See good fishing areas near you.',
      },
      'is-it-safe': {
        title: 'Is it safe?',
        description: 'Check sea conditions before you go.',
      },
      'sea-today': {
        title: 'Sea Today',
        description: 'See current weather, waves, wind and more.',
      },
      alerts: {
        title: 'Alerts',
        description: 'Check important warnings near you.',
      },
    },
    ask: {
      title: 'Ask ORCA',
      description: 'Ask anything about the sea, weather, fishing spots or safety.',
      suggestion: '“Where should I fish today?”',
    },
    nav: {
      home: 'Home',
      map: 'Map',
      ask: 'Ask',
      alerts: 'Alerts',
      profile: 'Profile',
    },
  },
  bn: {
    locationName: 'দিঘা, পশ্চিমবঙ্গ',
    locationDetected: 'অবস্থান শনাক্ত হয়েছে',
    location: {
      title: 'আপনার অবস্থান নির্ধারণ করুন',
      searchPlaceholder: 'বন্দর বা শহর খুঁজুন…',
      detect: 'আমার অবস্থান শনাক্ত করুন',
      detecting: 'আপনার অবস্থান খোঁজা হচ্ছে…',
      noResults: 'কোনো স্থান পাওয়া যায়নি',
      blocked: 'অবস্থানের অনুমতি বন্ধ আছে। অনুমতি দিন, বা উপরে খুঁজুন।',
      unavailable: 'আপনার অবস্থান পাওয়া যায়নি। বরং খুঁজে নিন।',
      current: 'বর্তমান',
      searching: 'খোঁজা হচ্ছে…',
    },
    greetings: {
      morning: 'সুপ্রভাত,',
      afternoon: 'শুভ দুপুর,',
      evening: 'শুভ সন্ধ্যা,',
    },
    fisherman: 'মৎস্যজীবী',
    mainQuestion: 'আজ আপনার কী প্রয়োজন?',
    cards: {
      'find-fish': {
        title: 'মাছ খুঁজুন',
        description: 'কাছের ভালো মাছ ধরার এলাকা দেখুন।',
      },
      'is-it-safe': {
        title: 'এটা কি নিরাপদ?',
        description: 'যাওয়ার আগে সমুদ্রের অবস্থা যাচাই করুন।',
      },
      'sea-today': {
        title: 'আজকের সমুদ্র',
        description: 'বর্তমান আবহাওয়া, ঢেউ, বাতাস ও আরও তথ্য।',
      },
      alerts: {
        title: 'সতর্কতা',
        description: 'জরুরি সামুদ্রিক সতর্কতা দেখুন।',
      },
    },
    ask: {
      title: 'ORCA-কে জিজ্ঞাসা করুন',
      description: 'সমুদ্র, আবহাওয়া, মাছ ধরার স্থান বা নিরাপত্তা নিয়ে জিজ্ঞাসা করুন।',
      suggestion: '“আজ কোথায় মাছ ধরতে যাব?”',
    },
    nav: {
      home: 'হোম',
      map: 'ম্যাপ',
      ask: 'জিজ্ঞাসা',
      alerts: 'সতর্কতা',
      profile: 'প্রোফাইল',
    },
  },
  ta: {
    locationName: 'திகா, மேற்கு வங்காளம்',
    locationDetected: 'இருப்பிடம் கண்டறியப்பட்டது',
    location: {
      title: 'உங்கள் இருப்பிடத்தை அமைக்கவும்',
      searchPlaceholder: 'துறைமுகம் அல்லது ஊரைத் தேடுங்கள்…',
      detect: 'எனது இருப்பிடத்தைக் கண்டறி',
      detecting: 'உங்கள் இருப்பிடம் தேடப்படுகிறது…',
      noResults: 'இடங்கள் கிடைக்கவில்லை',
      blocked: 'இருப்பிட அனுமதி தடுக்கப்பட்டுள்ளது. அனுமதிக்கவும் அல்லது மேலே தேடவும்.',
      unavailable: 'உங்கள் இருப்பிடத்தைப் பெற முடியவில்லை. தேடிப் பாருங்கள்.',
      current: 'தற்போதைய',
      searching: 'தேடுகிறது…',
    },
    greetings: {
      morning: 'காலை வணக்கம்,',
      afternoon: 'மதிய வணக்கம்,',
      evening: 'மாலை வணக்கம்,'
    },
    fisherman: 'மீனவர்',
    mainQuestion: 'இன்று உங்களுக்கு என்ன தேவை?',
    cards: {
      'find-fish': {
        title: 'மீன் தேடல்',
        description: 'அருகிலுள்ள நல்ல மீன்பிடி பகுதிகளைப் பாருங்கள்.',
      },
      'is-it-safe': {
        title: 'பாதுகாப்பானதா?',
        description: 'புறப்படுமுன் கடல் நிலையை அறியவும்.',
      },
      'sea-today': {
        title: 'இன்றைய கடல்',
        description: 'வானிலை, அலைகள் மற்றும் காற்று விவரங்கள்.',
      },
      alerts: {
        title: 'எச்சரிக்கைகள்',
        description: 'முக்கிய எச்சரிக்கை தகவல்களைக் காண்க.',
      },
    },
    ask: {
      title: 'ORCA-விடம் கேளுங்கள்',
      description: 'கடல், வானிலை, மீன்பிடி பகுதிகள் அல்லது பாதுகாப்பு பற்றி கேளுங்கள்.',
      suggestion: '“இன்று நான் எங்கு மீன்பிடிக்க வேண்டும்?”',
    },
    nav: {
      home: 'முகப்பு',
      map: 'வரைபடம்',
      ask: 'கேளுங்கள்',
      alerts: 'எச்சரிக்கைகள்',
      profile: 'சுயவிவரம்',
    },
  },
  te: {
    locationName: 'దిఘా, పశ్చిమ బెంగాల్',
    locationDetected: 'లొకేషన్ గుర్తించబడింది',
    location: {
      title: 'మీ స్థానాన్ని సెట్ చేయండి',
      searchPlaceholder: 'ఓడరేవు లేదా ఊరు వెతకండి…',
      detect: 'నా స్థానాన్ని గుర్తించు',
      detecting: 'మీ స్థానం వెతుకుతోంది…',
      noResults: 'స్థలాలు కనబడలేదు',
      blocked: 'స్థాన అనుమతి నిరోధించబడింది. అనుమతించండి లేదా పైన వెతకండి.',
      unavailable: 'మీ స్థానం పొందలేకపోయాము. బదులుగా వెతకండి.',
      current: 'ప్రస్తుత',
      searching: 'వెతుకుతోంది…',
    },
    greetings: {
      morning: 'శుభోదయం,',
      afternoon: 'శుభ మధ్యాహ్నం,',
      evening: 'శుభ సాయంత్రం,',
    },
    fisherman: 'మత్స్యకారుడు',
    mainQuestion: 'ఈ రోజు మీకు ఏమి కావాలి?',
    cards: {
      'find-fish': {
        title: 'చేపలను వెతకండి',
        description: 'మీ సమీపంలో మంచి చేపల ప్రాంతాలు చూడండి.',
      },
      'is-it-safe': {
        title: 'సురక్షితమేనా?',
        description: 'వెళ్లే ముందు సముద్ర పరిస్థితి తనిఖీ చేయండి.',
      },
      'sea-today': {
        title: 'నేటి సముద్రం',
        description: 'ప్రస్తుత వాతావరణం, అలలు, గాలుల సమాచారం.',
      },
      alerts: {
        title: 'హెచ్చరికలు',
        description: 'ముఖ్యమైన హెచ్చరికలను తనిఖీ చేయండి.',
      },
    },
    ask: {
      title: 'ORCAను అడగండి',
      description: 'సముద్రం, వాతావరణం, చేపల వేట ప్రాంతాలు లేదా భద్రత గురించి అడగండి.',
      suggestion: '“ఈ రోజు నేను ఎక్కడ వేటాడాలి?”',
    },
    nav: {
      home: 'హోమ్',
      map: 'మ్యాప్',
      ask: 'అడగండి',
      alerts: 'హెచ్చరికలు',
      profile: 'ప్రొఫైల్',
    },
  },
  ml: {
    locationName: 'ദിഘ, പശ്ചിമ ബംഗാൾ',
    locationDetected: 'ലൊക്കേഷൻ കണ്ടെത്തി',
    location: {
      title: 'നിങ്ങളുടെ സ്ഥാനം സജ്ജമാക്കുക',
      searchPlaceholder: 'തുറമുഖമോ പട്ടണമോ തിരയുക…',
      detect: 'എന്റെ സ്ഥാനം കണ്ടെത്തുക',
      detecting: 'നിങ്ങളുടെ സ്ഥാനം തിരയുന്നു…',
      noResults: 'സ്ഥലങ്ങളൊന്നും കണ്ടെത്തിയില്ല',
      blocked: 'സ്ഥാന അനുമതി തടഞ്ഞിരിക്കുന്നു. അനുവദിക്കുക, അല്ലെങ്കിൽ മുകളിൽ തിരയുക.',
      unavailable: 'നിങ്ങളുടെ സ്ഥാനം ലഭിച്ചില്ല. പകരം തിരയുക.',
      current: 'നിലവിലുള്ളത്',
      searching: 'തിരയുന്നു…',
    },
    greetings: {
      morning: 'സുപ്രഭാതം,',
      afternoon: 'ശുഭ ഉച്ച,',
      evening: 'ശുഭ സായാഹ്നം,',
    },
    fisherman: 'മത്സ്യത്തൊഴിലാളി',
    mainQuestion: 'ഇന്ന് നിങ്ങൾക്ക് എന്താണ് ആവശ്യം?',
    cards: {
      'find-fish': {
        title: 'മീൻ കണ്ടെത്തൂ',
        description: 'അടുത്തുള്ള മികച്ച മത്സ്യബന്ധന മേഖലകൾ കാണുക.',
      },
      'is-it-safe': {
        title: 'സുരക്ഷിതമാണോ?',
        description: 'കടലിൽ പോകും മുൻപ് സാഹചര്യം പരിശോധിക്കുക.',
      },
      'sea-today': {
        title: 'ഇന്നത്തെ കടൽ',
        description: 'കാലാവസ്ഥ, തിരമാല, കാറ്റ് വിവരങ്ങൾ അറിയുക.',
      },
      alerts: {
        title: 'മുന്നറിയിപ്പുകൾ',
        description: 'പ്രധാനപ്പെട്ട സമുദ്ര മുന്നറിയിപ്പുകൾ കാണുക.',
      },
    },
    ask: {
      title: 'ORCA-യോട് ചോദിക്കൂ',
      description: 'കടൽ, കാലാവസ്ഥ, മത്സ്യബന്ധന മേഖലകൾ, സുരക്ഷ എന്നിവ ചോദിക്കാം.',
      suggestion: '“ഇന്ന് ഞാൻ എവിടെ മീൻ പിടിക്കണം?”',
    },
    nav: {
      home: 'ഹോം',
      map: 'മാപ്പ്',
      ask: 'ചോദിക്കുക',
      alerts: 'അറിയിപ്പുകൾ',
      profile: 'പ്രൊഫൈൽ',
    },
  },
  mr: {
    locationName: 'दिघा, पश्चिम बंगाल',
    locationDetected: 'स्थान आढळले',
    location: {
      title: 'तुमचे स्थान निवडा',
      searchPlaceholder: 'बंदर किंवा गाव शोधा…',
      detect: 'माझे स्थान शोधा',
      detecting: 'तुमचे स्थान शोधत आहे…',
      noResults: 'कोणतीही ठिकाणे सापडली नाहीत',
      blocked: 'स्थान परवानगी बंद आहे. परवानगी द्या, किंवा वर शोधा.',
      unavailable: 'तुमचे स्थान मिळाले नाही. त्याऐवजी शोधा.',
      current: 'सध्याचे',
      searching: 'शोधत आहे…',
    },
    greetings: {
      morning: 'शुभ सकाळ,',
      afternoon: 'शुभ दुपार,',
      evening: 'शुभ संध्याकाळ,',
    },
    fisherman: 'मासेमार',
    mainQuestion: 'आज तुम्हाला कशाची गरज आहे?',
    cards: {
      'find-fish': {
        title: 'मासे शोधा',
        description: 'जवळची चांगली मासेमारीची ठिकाणे पहा.',
      },
      'is-it-safe': {
        title: 'सुरक्षित आहे का?',
        description: 'जाण्यापूर्वी समुद्राची परिस्थिती तपासा.',
      },
      'sea-today': {
        title: 'आजचा समुद्र',
        description: 'हवामान, लाटा आणि वाऱ्याची स्थिती पहा.',
      },
      alerts: {
        title: 'सूचना',
        description: 'महत्त्वाच्या सागरी सूचना पहा.',
      },
    },
    ask: {
      title: 'ORCA ला विचारा',
      description: 'समुद्र, हवामान, मासेमारी क्षेत्र किंवा सुरक्षेबद्दल विचारा.',
      suggestion: '“आज मी कुठे मासेमारी करावी?”',
    },
    nav: {
      home: 'होम',
      map: 'नकाशा',
      ask: 'विचारा',
      alerts: 'सूचना',
      profile: 'प्रोफाइल',
    },
  },
  gu: {
    locationName: 'દીઘા, પશ્ચિમ બંગાળ',
    locationDetected: 'સ્થાન શોધાયું',
    location: {
      title: 'તમારું સ્થાન સેટ કરો',
      searchPlaceholder: 'બંદર અથવા ગામ શોધો…',
      detect: 'મારું સ્થાન શોધો',
      detecting: 'તમારું સ્થાન શોધી રહ્યા છીએ…',
      noResults: 'કોઈ સ્થળ મળ્યું નથી',
      blocked: 'સ્થાન પરવાનગી બંધ છે. પરવાનગી આપો, અથવા ઉપર શોધો.',
      unavailable: 'તમારું સ્થાન મળ્યું નહીં. તેના બદલે શોધો.',
      current: 'વર્તમાન',
      searching: 'શોધી રહ્યું છે…',
    },
    greetings: {
      morning: 'શુભ સવાર,',
      afternoon: 'શુભ બપોર,',
      evening: 'શુભ સાંજ,',
    },
    fisherman: 'માછીમાર',
    mainQuestion: 'આજે તમારે શું જોઈએ છે?',
    cards: {
      'find-fish': {
        title: 'માછલી શોધો',
        description: 'નજીકના સારા માછીમારી વિસ્તારો જુઓ.',
      },
      'is-it-safe': {
        title: 'શું સુરક્ષિત છે?',
        description: 'જતાં પહેલાં સમુદ્રની સ્થિતિ તપાસો.',
      },
      'sea-today': {
        title: 'આજનો દરિયો',
        description: 'હવામાન, મોજાં અને પવનની સ્થિતિ જુઓ.',
      },
      alerts: {
        title: 'ચેતવણીઓ',
        description: 'મહત્વપૂર્ણ દરિયાઈ ચેતવણીઓ જુઓ.',
      },
    },
    ask: {
      title: 'ORCA ને પૂછો',
      description: 'સમુદ્ર, હવામાન, માછીમારી સ્થળો કે સુરક્ષા વિશે પૂછો.',
      suggestion: '“આજે મારે ક્યાં માછીમારી કરવી જોઈએ?”',
    },
    nav: {
      home: 'હોમ',
      map: 'નકશો',
      ask: 'પૂછો',
      alerts: 'ચેતવણીઓ',
      profile: 'પ્રોફાઇલ',
    },
  },
  hi: {
    locationName: 'दीघा, पश्चिम बंगाल',
    locationDetected: 'स्थान का पता चला',
    location: {
      title: 'अपना स्थान चुनें',
      searchPlaceholder: 'बंदरगाह या शहर खोजें…',
      detect: 'मेरा स्थान पता करें',
      detecting: 'आपका स्थान खोजा जा रहा है…',
      noResults: 'कोई स्थान नहीं मिला',
      blocked: 'स्थान की अनुमति बंद है। अनुमति दें, या ऊपर खोजें।',
      unavailable: 'आपका स्थान नहीं मिल सका। इसके बजाय खोजें।',
      current: 'वर्तमान',
      searching: 'खोज रहे हैं…',
    },
    greetings: {
      morning: 'सुप्रभात,',
      afternoon: 'शुभ दोपहर,',
      evening: 'शुभ संध्या,',
    },
    fisherman: 'मछुआरे',
    mainQuestion: 'आज आपको क्या चाहिए?',
    cards: {
      'find-fish': {
        title: 'मछली खोजें',
        description: 'अपने पास मछली पकड़ने के अच्छे क्षेत्र देखें।',
      },
      'is-it-safe': {
        title: 'क्या यह सुरक्षित है?',
        description: 'जाने से पहले समुद्र की स्थिति जांचें।',
      },
      'sea-today': {
        title: 'आज का समुद्र',
        description: 'मौसम, लहरें और हवा की स्थिति देखें।',
      },
      alerts: {
        title: 'अलर्ट',
        description: 'महत्वपूर्ण समुद्री चेतावनी देखें।',
      },
    },
    ask: {
      title: 'ORCA से पूछें',
      description: 'समुद्र, मौसम, मछली पकड़ने के स्थान या सुरक्षा के बारे में पूछें।',
      suggestion: '“आज मुझे कहाँ मछली पकड़नी चाहिए?”',
    },
    nav: {
      home: 'होम',
      map: 'मैप',
      ask: 'पूछें',
      alerts: 'अलर्ट',
      profile: 'प्रोफ़ाइल',
    },
  },
  or: {
    locationName: 'ଦିଘା, ପଶ୍ଚିମବଙ୍ଗ',
    locationDetected: 'ଅବସ୍ଥିତି ଚିହ୍ନଟ ହୋଇଛି',
    location: {
      title: 'ଆପଣଙ୍କ ଅବସ୍ଥାନ ସେଟ୍ କରନ୍ତୁ',
      searchPlaceholder: 'ବନ୍ଦର କିମ୍ବା ସହର ଖୋଜନ୍ତୁ…',
      detect: 'ମୋ ଅବସ୍ଥାନ ଚିହ୍ନଟ କରନ୍ତୁ',
      detecting: 'ଆପଣଙ୍କ ଅବସ୍ଥାନ ଖୋଜାଯାଉଛି…',
      noResults: 'କୌଣସି ସ୍ଥାନ ମିଳିଲା ନାହିଁ',
      blocked: 'ଅବସ୍ଥାନ ଅନୁମତି ବନ୍ଦ ଅଛି। ଅନୁମତି ଦିଅନ୍ତୁ, କିମ୍ବା ଉପରେ ଖୋଜନ୍ତୁ।',
      unavailable: 'ଆପଣଙ୍କ ଅବସ୍ଥାନ ମିଳିଲା ନାହିଁ। ଏହା ପରିବର୍ତ୍ତେ ଖୋଜନ୍ତୁ।',
      current: 'ବର୍ତ୍ତମାନ',
      searching: 'ଖୋଜୁଛି…',
    },
    greetings: {
      morning: 'ଶୁଭ ସକାଳ,',
      afternoon: 'ଶୁଭ ଅପରାହ୍ନ,',
      evening: 'ଶୁଭ ସନ୍ଧ୍ୟା,',
    },
    fisherman: 'ମତ୍ସ୍ୟଜୀବୀ',
    mainQuestion: 'ଆଜି ଆପଣଙ୍କୁ କ’ଣ ଦରକାର?',
    cards: {
      'find-fish': {
        title: 'ମାଛ ଖୋଜନ୍ତୁ',
        description: 'ନିକଟସ୍ଥ ଭଲ ମାଛ ଧରିବା ସ୍ଥାନ ଦେଖନ୍ତୁ।',
      },
      'is-it-safe': {
        title: 'ଏହା ନିରାପଦ କି?',
        description: 'ଯିବା ପୂର୍ବରୁ ସମୁଦ୍ରର ସ୍ଥିତି ଯାଞ୍ଚ କରନ୍ତୁ।',
      },
      'sea-today': {
        title: 'ଆଜିର ସମୁଦ୍ର',
        description: 'ସାମ୍ପ୍ରତିକ ପାଣିପାଗ, ତରଙ୍ଗ ଓ ପବନର ସୂଚନା।',
      },
      alerts: {
        title: 'ସତର୍କତା',
        description: 'ଜରୁରୀ ସାମୁଦ୍ରିକ ଚେତାବନୀ ଦେଖନ୍ତୁ।',
      },
    },
    ask: {
      title: 'ORCA କୁ ପଚାରନ୍ତୁ',
      description: 'ସମୁଦ୍ର, ପାଣିପାଗ, ମାଛ ଧରିବା ସ୍ଥାନ କିମ୍ବା ନିରାପତ୍ତା ବିଷୟରେ ପଚାରନ୍ତୁ।',
      suggestion: '“ଆଜି ମୁଁ କେଉଁଠି ମାଛ ଧରିବାକୁ ଯିବି?”',
    },
    nav: {
      home: 'ହୋମ୍',
      map: 'ମାନଚିତ୍ର',
      ask: 'ପଚାରନ୍ତୁ',
      alerts: 'ସତର୍କତା',
      profile: 'ପ୍ରୋଫାଇଲ୍',
    },
  },
};

export const getHomeTranslation = (langCode?: string): HomeTranslation => {
  if (!langCode || !HOME_TRANSLATIONS[langCode]) {
    return HOME_TRANSLATIONS.en;
  }
  return HOME_TRANSLATIONS[langCode];
};

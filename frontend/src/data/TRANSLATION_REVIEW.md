# Translation review — safety wording

Machine translation is good enough for a button label and **not** good enough for a
word that changes what somebody does at sea. Round-tripping an earlier pass back to
English turned `MODERATE SEA` into *Mediterranean* and `Avoid` into *Check*.

Every string below carries safety meaning. Each needs one native speaker to read it
and say yes or no. Correct any that are wrong directly in the screen's own
`*Data.ts` table — a hand-written entry there takes precedence over the generated
file and will survive regeneration.

28 strings, 85 translations to check.

### `Alert state:`

| language | translation | ok? |
|---|---|---|
| Gujarati | ચેતવણી સ્થિતિ: |  |
| Marathi | सतर्क अवस्था: |  |
| Odia | ସତର୍କ ଅବସ୍ଥା: |  |

### `Avoid`

| language | translation | ok? |
|---|---|---|
| Gujarati | ટાળો |  |
| Malayalam | ഒഴിവാക്കുക |  |
| Marathi | टाळा |  |
| Odia | ପରିହାର |  |

### `Avoid area • Storm risk`

| language | translation | ok? |
|---|---|---|
| Gujarati | વિસ્તાર • વાવાઝોડાનું જોખમ ટાળો |  |
| Marathi | क्षेत्र • वादळाचा धोका टाळा |  |
| Odia | ଏରିଆ ଏଡ଼ାଇବା • ଝଡ଼ର ବିପଦ |  |

### `Avoid going far offshore`

| language | translation | ok? |
|---|---|---|
| Gujarati | દૂર દરિયામાં ન જવું જોઈએ. |  |
| Marathi | दूर समुद्रात जाणे टाळा. |  |
| Odia | ଦୂର ସମୁଦ୍ରକୁ ଯିବା ଏଡ଼ାଇବା ଉଚିତ୍ । |  |

### `CALM SEA`

| language | translation | ok? |
|---|---|---|
| Gujarati | શાંત સમુદ્ર |  |
| Marathi | शांत समुद्र |  |
| Odia | ଶାନ୍ତ ସମୁଦ୍ର |  |

### `CAUTION`

| language | translation | ok? |
|---|---|---|
| Gujarati | સાવધાની |  |
| Marathi | खबरदारी |  |
| Odia | ସତର୍କତା |  |

### `Calm sea (0.8m wave, safe)`

| language | translation | ok? |
|---|---|---|
| Gujarati | શાંત સમુદ્ર (0.તરંગ, સલામત) |  |
| Malayalam | ശാന്തമായ കടൽ (0.തരംഗം, സുരക്ഷിതം) |  |
| Marathi | शांत समुद्र (0).8mलहरी, सुरक्षित) |  |

### `Calm waters right now. Waves 0.8m, wind 12 km/h. Good day for fishing.`

| language | translation | ok? |
|---|---|---|
| Gujarati | શાંત પાણી, અત્યારે. મોજા 0.8m, પવન12 km/h. માછીમારી માટે શુભ દિવસ. |  |
| Marathi | शांत रहा, सध्या. लहरी 0.8m, वारा12 km/h. मासेमारीसाठी शुभ दिवस आहे. |  |
| Odia | ଶାନ୍ତ ରୁହନ୍ତୁ, ଏବେ। ଲହଡ଼ିଗୁଡ଼ିକ 0।8m, ପବନ12 km/h. ମାଛଧରା ପାଇଁ ଶୁଭ ଦିନ। |  |

### `Conditions are safe until 2 PM. Avoid going far offshore after 2 PM due to strong winds.`

| language | translation | ok? |
|---|---|---|
| Gujarati | 2 વાગ્યા સુધી સ્થિતિ સુરક્ષિત છે. ભારે પવનને કારણે બપોરના 2 વાગ્યા પછી દરિયાકાંઠે દૂર ન જવાય તેનું ધ્યાન રાખજો. |  |
| Marathi | दुपारी 2 वाजेपर्यंत परिस्थिती सुरक्षित आहे. दुपारी 2 नंतर जोरदार वाऱ्यामुळे दूर समुद्रात जाणे टाळावे. |  |
| Odia | 2ଟା ପର୍ଯ୍ୟନ୍ତ ପରିସ୍ଥିତି ସୁରକ୍ଷିତ ଅଛି। ପ୍ରବଳ ପବନ ଯୋଗୁଁ ଅପରାହ୍ନ 2ଟା ପରେ ଦୂର ସମୁଦ୍ରକୁ ଯିବାଠାରୁ ଦୂରେଇ ରୁହନ୍ତୁ। |  |

### `Good fish conditions + safe sea`

| language | translation | ok? |
|---|---|---|
| Gujarati | સારી માછલીની સ્થિતિ અને સલામત સમુદ્ર |  |
| Malayalam | നല്ല മത്സ്യസാഹചര്യങ്ങളും സുരക്ഷിതമായ കടലും |  |
| Marathi | चांगली मासेमारीची परिस्थिती आणि सुरक्षित समुद्र |  |

### `HIGH ALERT`

| language | translation | ok? |
|---|---|---|
| Gujarati | ભયભીત |  |
| Marathi | धोक्याचा इशारा |  |
| Odia | ଆତଙ୍କ |  |

### `High alert: Strong winds expected after 2 PM. Avoid going far offshore.`

| language | translation | ok? |
|---|---|---|
| Gujarati | ઉચ્ચ ચેતવણી: બપોરના 2 વાગ્યા પછી ભારે પવન ફૂંકાવાની સંભાવના છે. દૂર દરિયામાં ન જવું. |  |
| Marathi | उच्च इशारा: दुपारी 2 नंतर जोरदार वारे येण्याचा अंदाज आहे. दूरवरच्या समुद्रात जाणे टाळा. |  |
| Odia | ଉଚ୍ଚ ସତର୍କତା: ଅପରାହ୍ନ 2ଟା ପରେ ପ୍ରବଳ ପବନ ଆଶଙ୍କା କରାଯାଉଛି। ଦୂର ସମୁଦ୍ରକୁ ଯିବାଠାରୁ ଦୂରେଇ ରୁହନ୍ତୁ। |  |

### `IMD coastal squall warning active for Digha-Midnapore maritime belt from 2 PM.`

| language | translation | ok? |
|---|---|---|
| Gujarati | IMDસાંજે 2 વાગ્યાથી દીઘા-મિદનાપુર દરિયાઈ વિસ્તારમાં દરિયાકાંઠાની તોફાનની ચેતવણી સક્રિય છે. |  |
| Marathi | दुपारी 2 वाजल्यापासून दीघा-मिदनापूर सागरी पट्ट्यासाठी किनारपट्टीवर चक्रीवादळाचा इशारा सक्रिय आहे. |  |
| Odia | IMDଡିଗାମଧ୍ୟସ୍ଥ-ମିଡ଼୍‌ନପୁର ସାମୁଦ୍ରିକ କ୍ଷେତ୍ର ପାଇଁ ଅପରାହ୍ନ 2ଟାରୁ ସାମୁଦ୍ରିକ ଝଡ଼ ସତର୍କତା ଜାରି କରାଯାଇଛି । |  |

### `Is it safe today?`

| language | translation | ok? |
|---|---|---|
| Gujarati | આજે સુરક્ષિત છે? |  |
| Marathi | आज सुरक्षित आहे का? |  |
| Odia | ଆଜି ସୁରକ୍ଷିତ ଅଛି କି? |  |

### `MODERATE SEA`

| language | translation | ok? |
|---|---|---|
| Gujarati | મધ્યમ સમુદ્ર |  |
| Marathi | मध्यम समुद्र |  |
| Odia | ମଧ୍ୟମ ସମୁଦ୍ର |  |

### `Moderate chance`

| language | translation | ok? |
|---|---|---|
| Gujarati | મધ્યમ તક |  |
| Malayalam | മിതമായ സാധ്യത |  |
| Marathi | मध्यम शक्यता |  |

### `Moderate conditions`

| language | translation | ok? |
|---|---|---|
| Gujarati | મધ્યમ પરિસ્થિતિઓ |  |
| Marathi | मध्यम परिस्थिती |  |
| Odia | ମଧ୍ୟମ |  |

### `ROUGH SEA`

| language | translation | ok? |
|---|---|---|
| Gujarati | તોફાન |  |
| Marathi | उग्र समुद्र |  |
| Odia | ଝଡ଼ |  |

### `Rough conditions`

| language | translation | ok? |
|---|---|---|
| Gujarati | ખરાબ પરિસ્થિતિ |  |
| Marathi | खराब परिस्थिती |  |
| Odia | ଖରାପ ପରିସ୍ଥିତି |  |

### `Rough sea expected. Avoid going out.`

| language | translation | ok? |
|---|---|---|
| Gujarati | ખરબચડા સમુદ્રની અપેક્ષા છે. બહાર જવાનું ટાળો. |  |
| Marathi | समुद्र खवळण्याची शक्यता आहे. बाहेर जाणे टाळा. |  |
| Odia | ସମୁଦ୍ରରେ ପ୍ରବଳ ଲହଡ଼ି ଆଶଙ୍କା ରହିଛି। ବାହାରକୁ ଯିବାଠାରୁ ଦୂରେଇ ରୁହନ୍ତୁ। |  |

### `Safe to go`

| language | translation | ok? |
|---|---|---|
| Gujarati | જવા માટે અનુકૂળતા |  |
| Marathi | जाण्यासाठी सुरक्षित आहे. |  |
| Odia | ଯିବା ପାଇଁ ସୁରକ୍ଷିତ |  |

### `Sea State Simulator:`

| language | translation | ok? |
|---|---|---|
| Gujarati | સમુદ્ર રાજ્ય અનુકરણકર્તા: |  |
| Marathi | सागरी राज्य अनुकरणकर्ता: |  |
| Odia | ସାମୁଦ୍ରିକ ରାଜ୍ୟ ସିମୁଲେଟର: |  |

### `Stay close to shore and avoid going far offshore after 2 PM.`

| language | translation | ok? |
|---|---|---|
| Gujarati | કિનારાની નજીક રહો અને બપોર 2 વાગ્યા પછી દૂર દરિયામાં ન જવું. |  |
| Marathi | किनाऱ्याजवळ राहा आणि दुपारी 2 नंतर दूरवर जाणे टाळा. |  |
| Odia | କୂଳ ନିକଟରେ ରୁହନ୍ତୁ ଏବଂ ଅପରାହ୍ନ 2ଟା ପରେ ବହୁଦୂର ସମୁଦ୍ର ଭିତରକୁ ଯିବାରୁ ଦୂରେଇ ରୁହନ୍ତୁ। |  |

### `Stay informed. Stay safe.`

| language | translation | ok? |
|---|---|---|
| Gujarati | માહિતગાર રહો. સુરક્ષિત રહો. |  |
| Marathi | जागरूक राहा. सुरक्षित राहा. |  |
| Odia | ଅବଗତ ରୁହନ୍ତୁ। ସୁରକ୍ଷିତ ରୁହନ୍ତୁ। |  |

### `Try the green area, 12 km offshore. Sea conditions are safe.`

| language | translation | ok? |
|---|---|---|
| Gujarati | લીલા વિસ્તાર,12 kmઓફશોરનો પ્રયાસ કરો. દરિયાઈ સ્થિતિ સલામત છે. |  |
| Marathi | हिरव्या भागावर,12 kmऑफशोअर प्रयत्न करा. सागरी परिस्थिती सुरक्षित आहे. |  |
| Odia | ଗ୍ରୀନ୍ ଏରିଆ,12 kmଅଫ୍‌ଶୋର ଚେଷ୍ଟା କରନ୍ତୁ। ସମୁଦ୍ର ପରିସ୍ଥିତି ନିରାପଦ। |  |

### `Want to know what this alert means?`

| language | translation | ok? |
|---|---|---|
| Gujarati | આ ચેતવણીનો અર્થ શું છે તે જાણવા માંગો છો? |  |
| Marathi | या अलर्टचा अर्थ काय आहे हे जाणून घ्यायचे आहे का? |  |
| Odia | ଏହି ସତର୍କତାର ଅର୍ଥ କ’ଣ ଜାଣିବାକୁ ଇଚ୍ଛା କରୁଛନ୍ତି କି? |  |

### `Water temperature is 27.5°C with high chlorophyll and moderate currents, attracting mackerel and hilsa.`

| language | translation | ok? |
|---|---|---|
| Gujarati | પાણીનું તાપમાન 27 ડિગ્રી છે.ઉચ્ચ ક્લોરોફિલ અને મધ્યમ પ્રવાહો સાથે, મેકરેલ અને હિલસાને આકર્ષિત કરતી5°C. |  |
| Marathi | पाण्याचे तापमान 27 आहे.5°C उच्च क्लोरोफिल आणि मध्यम प्रवाहांसह, मॅककेरल आणि हिलसा आकर्षित करते. |  |
| Odia | ପାଣିର ତାପମାତ୍ରା 27 ଅଟେ।5°C ଉଚ୍ଚ କ୍ଲୋରୋଫିଲ୍ ଏବଂ ମଧ୍ୟମ ପ୍ରବାହ ସହିତ, ମାକେରେଲ୍ ଏବଂ ହିଲ୍‌ସାକୁ ଆକୃଷ୍ଟ କରିଥାଏ। |  |

### `Winds will start picking up after 1:30 PM and exceed 38 km/h by 2 PM. High swell is expected 8–12 km offshore. Return to shore before 2 PM.`

| language | translation | ok? |
|---|---|---|
| Gujarati | બપોરના 1:30 વાગ્યા પછી પવન વધવા લાગશે અને બપોરના 2 વાગ્યા સુધીમાં38 km/h થી વધી જશે. દરિયાકાંઠે ઊંચા મોજાંઓ અપેક્ષિત છે8–12 km. બપોરના બે વાગ્યા પહેલાં કિનારે પાછા ફરો. |  |
| Marathi | दुपारी 1:30 वाजता वाऱ्याचा वेग वाढू लागेल आणि दुपारी 2 वाजेपर्यंत38 km/h पेक्षा जास्त होईल. उच्च लाट @1@@offshore अपेक्षित आहे. दुपारी 2 वाजण्यापूर्वी किनाऱ्यावर परत या. |  |
| Odia | ଅପରାହ୍ନ 1:30 ପରେ ପବନ ବହିବା ଆରମ୍ଭ ହେବ ଏବଂ ଅପରାହ୍ନ 2ଟା ସୁଦ୍ଧା ଘଣ୍ଟା ପ୍ରତି38 km/h ଅତିକ୍ରମ କରିବ । ଉଚ୍ଚ ସ୍ରୋତ8–12 kmଉପକୂଳବର୍ତ୍ତୀ ଅଞ୍ଚଳରେ ଅନୁଭୂତ ହେବାର ସମ୍ଭାବନା ରହିଛି । ଅପରାହ୍ନ 2ଟା ପୂର୍ବରୁ କୂଳକୁ ଫେରିଯାନ୍ତୁ । |  |

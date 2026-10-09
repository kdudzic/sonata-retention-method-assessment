<!-- prompt_version: lexicon_expand_v1 | Annex G: LLM expands the S0 lexicon from the CATEGORY DEFINITIONS, never from corpus texts. Output is a draft pruned by hand and frozen. -->
SYSTEM
You help build a lexical pattern list for a Polish-language keyword selector used in a research study on data-retention filters. You receive category definitions and must propose Polish surface forms for each category. You must rely only on the definitions and your knowledge of Polish; you are not shown any corpus text. Output strict JSON only.

USER
Produce Polish lexical entries for the following categories. Each entry is a lower-case word or short phrase as it would appear in informal online posts, without diacritics being required (both "pojde" and "pójdę" will be matched after normalisation, so give the standard spelling). Use a trailing "*" on a word to allow any inflectional ending (e.g. "spakowan*" matches spakowane/spakowany/spakowana). Give 40-80 entries per category, covering inflection and colloquial variants.

Category A - first-person agency: the speaker presents a possible action as their own: first-person singular or plural future or modal forms of action verbs (going, doing, coming, taking care of, showing someone, settling scores, visiting someone with a purpose), promises and oaths ("przysięgam, że", "obiecuję"), "you'll see / you'll find out" forms addressed to a target ("zobaczysz", "przekonasz się", "pożałujesz"). Do NOT include generic everyday verbs that are first person but carry no action toward anyone (eating, sleeping, buying food, watching TV).

Category B_nouns - concrete target nouns: common nouns denoting an identifiable person, institution, place, object or event that could be a target: school, office, clinic, bank, shop/venue on a corner, stop, station, depot, warehouse, rail siding, bridge, substation, church-type public buildings only if generic words, director, teacher, doctor, boss, neighbour, ex-partner, named-kin words used as a target ("brat", "żona" only if combined with an action; include them), event words (match, concert, rally, fair). Give the base noun with "*" for inflection.

Category B_possessive - possessive/deictic determiners that point at a specific target when combined with a B noun: "ich", "jego", "jej", "tego", "tej", "tamtego", "naszego dyrektora"-style determiners (give only the determiners).

Category C - temporal proximity, a CLOSED list: today, tonight, tomorrow, in an hour, after school, after the match, this evening, on Saturday (all weekday names in all common case forms: "w sobotę", "w piątek", "we wtorek", "w czwartek"), "zaraz", "za chwilę", "jeszcze dziś", "do piątku", "w weekend", "jutro rano", "wieczorem", "o 18", specific clock-time patterns (give as regex with prefix "re:" e.g. "re:\bo \d{1,2}(:\d{2})?\b").

Category D - readiness / capability / access: "mam dostęp", "wiem gdzie", "wiem kiedy", "już spakowane", "jestem w drodze", "mam klucze", "mam kod", "mam adres", "załatwione", "kupione", "gotowe", "wszystko przygotowane", "sprawdziłem kiedy", "odłożyłem tyle", "wystarczy", first-person forms of having/obtaining means, knowing routines of someone ("wiem o której wraca").

Category E - DISCARD signals (reported speech, attribution, news context, satire, lyrics, counterspeech): "podobno", "rzekomo", "według", "policja podała", "jak podaje", "mówił, że", "napisał, że", "pisze, że", "cytat", "cytuję", "nagłówek", "z artykułu", "w wiadomościach", "w TVN", "tekst piosenki", "refren", "jak w filmie", "jak w serialu", "żart", "ironicznie", "sarkazm", "nikt nie powinien", "to straszne, że ktoś", "potępiam", "nie wolno grozić", "gdyby" (hypothetical), "hipotetycznie", "haha" is NOT included. Also reporting verbs in third person ("groził", "zapowiedział", "ogłosił") and media words ("reporter", "redakcja", "portal").

Return a JSON object with keys "A", "B_nouns", "B_possessive", "C", "D", "E", each an array of strings.

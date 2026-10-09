# 21.08.26

## Pierwsze kroki

1. Mamy dobre istniejące datasety!

- Offenseval

  - https://arxiv.org/abs/1903.08983
  - https://github.com/joeykay9/offenseval

- YouTube Threat Corpus

  - https://ieeexplore.ieee.org/document/8877435
  - https://github.com/erikve/YouTube-Threat-Corpus/tree/master/Articles

- ThreatCore (best)

  - https://arxiv.org/abs/2605.10563
  - https://github.com/DavideBruni/ThreatCore

## To wszystko można rozwiązać datasetem

2. Napisanie przez kogoś ok. 50 przypadków celowych lub ekstrakcja ich z istniejącego datasetu.
3. Eksploracja metod generacji syntetycznych przykładów.
4. Dodatkowe dobre sprawdzenie generacji treści "okołozagrożeniowych". Jak dobrze modele radzą sobie z tym konceptem?

## Osobne

5. Jak generować łuki? Osobno, czy od razu z przypadkami? Jeśli mamy dataset, to na podstawie przykładów. Modele do tego jednak mogą nie być dobre, chyba, że historia nie ma zawierać treści zabronionych?
6. Czy mamy tutaj jakieś wytyczne co do preferowanej treści wpisów? Tzn. czy model ma się kierować jakimś zestawem zmiennych przy generacji tak, jak robiliśmy to wcześniej?
7. Jeśli zdecydujemy się na dane z istniejącego korpusu, to trzeba sprawdzić kontaminację na potencjalnie wykorzystywalnych modelach.

# EP-SKEL, pilotaż: podsumowanie na jednej stronie

2026-10-28 · Kacper Dudzic · pełny raport (po angielsku) w `notes/results_report_20261027.md`

Korpus liczy 4032 polskie wpisy 196 autorów. Zawiera 10 łuków celowych, z czego 4 są skoncentrowane, a 6 rozproszonych,
do tego 2 profile mylące i 184 autorów postronnych. Każdy budżet zatrzymuje górne 1 %, 5 % albo 20 % wpisów, czyli 40,
202 albo 806 wpisów.

## Wyniki według selektora

| Selektor | Model | Dostęp | Wykryte łuki przy 1 % / 5 % / 20 % | Wykryte łuki rozproszone przy 20 %, z 6 | Autorzy postronni przy 20 % | Łuki zatrzymane decyzją KEEP, rozproszone w nawiasie | Autorzy postronni zatrzymani decyzją |
|---|---|---|---|---|---|---|---|
| S-rand | losowy, 5 ziaren | D0 | 0,4 / 1,6 / 4,6 | 3,6 | 178 | brak | brak |
| S0 leksykalny, sub | zamrożona lista słów | D0 | 2,0 / 3,7 / 9,0 | 6,0 | 177 | brak | brak |
| S0 leksykalny, sub | zamrożona lista słów | D3-agg | 0,0 / 0,0 / 3,7 | 2,7 | 88 | brak | brak |
| S1 semantyczny | Qwen3-Embedding-8B | D0 | 4 / 8 / 9 | 5 | 179 | brak | brak |
| S1 semantyczny | Qwen3-Embedding-8B | D3-txt | 0 / 2 / 5 | 3 | 126 | brak | brak |
| S3-open | Qwen3.8 27B | D0 | 7 / 8 / 10 | 6 | 160 | 7 [3] | 19 |
| S3-open | Qwen3.8 27B | D3-nat | 7 / 9 / 10 | 6 | 109 | 7 [3] | 31 |
| S3' zaślepiony | Qwen3.8 27B | D0 | 6 / 8 / 10 | 6 | 154 | 6 [2] | 30 |
| S3' zaślepiony | Qwen3.8 27B | D3-nat | 6 / 8 / 10 | 6 | 104 | 8 [4] | 42 |
| S3-com kontrolny | Gemini 3.1 Pro | D0, próba 10 % | nieporównywalne | nieporównywalne | nieporównywalne | 7 [3] | 1 |
| S3-com kontrolny | Gemini 3.1 Pro | D3-nat, próba 10 % | nieporównywalne | nieporównywalne | nieporównywalne | 8 [4] | 1 |

D0 oznacza, że selektor widzi sam wpis. Warianty D3 dają mu także wcześniejsze wpisy autora. D3-nat umieszcza tę
historię w promptcie modelu, D3-txt w oknie enkodera, a D3-agg sumuje trzy najwyższe wyniki wpisów autora. Łuk uznajemy
za wykryty, gdy co najmniej jeden jego wpis sygnałowy trafia do zbioru zatrzymanego. Wartości to średnie po ziarnach
rozstrzygania remisów. S0 i S1 nie wydają decyzji KEEP, więc dwie ostatnie kolumny są dla nich puste. Model kontrolny
ocenił próbę 426 wpisów, dlatego jego wyników budżetowych nie porównujemy z pozostałymi wierszami.

## Najważniejsze

- **Kontrole dodatnie działają.** S0 wykrywa 3 z 4 łuków skoncentrowanych na podstawie samego wpisu, a każdy selektor
  LLM wykrywa wszystkie 4. Żaden profil mylący nie zostaje zatrzymany decyzją. Wybór losowy wykrywa 0,4 łuku przy
  budżecie 1 %.
- **Selektory LLM nasycają widok budżetowy.** Przy 5 % wykrywają 8 lub 9 łuków z historią i bez niej. Każdy
  niebanalny wpis mieści się w tak małym budżecie, bo trudne negatywy stanowią 14 % korpusu.
- **Historia zwiększa liczbę zatrzymanych osób postronnych, co odpowiada H4.** W widoku decyzyjnym liczba
  zatrzymanych autorów postronnych rośnie z 19 do 31 dla S3-open i z 30 do 42 dla S3'. Przy stałym budżecie 20 %
  S3-open rozkłada tę samą objętość danych na 109 autorów z historią zamiast 160, więc każdy zatrzymany profil jest
  głębszy.
- **Historia dodaje łuki rozproszone, co odpowiada H3, dla dwóch z trzech selektorów LLM.** W widoku decyzyjnym S3'
  przechodzi z 2 do 4 łuków rozproszonych, a Gemini z 3 do 4. S3-open zatrzymuje 3 z historią i bez niej.
- **Jawna lista sygnałów hamuje model.** Z historią S3' zatrzymuje 84 wpisy, a S3-open 48.
- **Wyniki S1 i D3-agg nie są czyste.** Zamrożone opisy zalążkowe S1 parafrazują wzorce łuków, a z przetasowanymi
  opisami S1 wykrywa od 0 do 2 łuków. Agregacja top-3 premiuje autorów, którzy dużo piszą.
- **Z sześciu kryteriów go / no-go dwa są spełnione, trzy nie, a jedno nie ma jeszcze progu.** Kryterium 4 wymaga,
  by wybór losowy wykrywał najwyżej 1 łuk przy 20 %, co jest niemożliwe przy 1 do 5 wpisach sygnałowych na łuk.
  Kryteria 2 i 5 nie są spełnione z powodu opisanego wyżej nasycenia.
- **Przebiegi są powtarzalne i tanie.** Dwa przebiegi S3-open zgadzają się w 100 % decyzji. Model kontrolny zgadza
  się z S3-open w 98 do 99,5 % decyzji. Cały pilotaż kosztował 88,90 USD przez OpenRouter.
- **Przed pełną skalą potrzebne są cztery zmiany.** Autorzy łuków powinni mieć tyle wpisów co pozostali autorzy.
  Opisy zalążkowe S1 trzeba napisać wyłącznie na podstawie reguł decyzyjnych. Budżety należy dobrać do udziału
  trudnych negatywów. Widok decyzyjny powinien być raportowany obok budżetowego jako miara główna.

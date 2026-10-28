# EP-SKEL wyniki

## Koncept

Symulujemy automatyczny selektor, który przegląda wpisy w mediach społecznościowych i decyduje, które zachować do dalszej analizy. Interesują nas dwie rzeczy: ile groźnych sytuacji selektor wykrywa i ilu niezwiązanych z nimi osób dane przy tym zatrzymuje. Główne pytanie brzmi: czy selektor, który oprócz pojedynczego wpisu widzi też wcześniejsze wpisy tego samego autora, wykrywa więcej.

## Hipotezy

Brzmienie z planu badania (sekcja 2). W pilotażu hipotez nie testujemy statystycznie, a jedynie sprawdzamy, czy efekty
występują w oczekiwanym kierunku.

- **Teza główna.** Obietnica ograniczenia zakresu gromadzonych danych dzięki AI nie jest redukcją inwazyjności, lecz jej przeniesieniem: zawężenie na poziomie pojedynczego wpisu zostaje okupione koniecznością sięgnięcia po historię wypowiedzi autora.
- **H1.** Krzywa wykrywalności nasyca się przy budżecie retencyjnym istotnie niższym niż 100 %.
- **H2.** Przy równym budżecie retencyjnym selektor LLM ma wyższą wykrywalność niż selektor leksykalny, ale gorszą gradację rankingu (liczne remisy nie występują tylko u S0).
- **H3 (kluczowa).** Wykrywalność łuków o sygnale rozproszonym rośnie skokowo przy przejściu z dostępu do pojedynczego wpisu (D0) na dostęp do historii autora (D3); dla łuków skoncentrowanych przyrost jest marginalny.
- **H4.** Przyrost wykrywalności z D0 na D3 jest okupiony nieproporcjonalnym wzrostem liczby autorów-niecelów objętych retencją oraz głębokości ich profili.

## Korpus

- Sztucznie wygenerowany, polskojęzyczny korpus. Model generujący: `GPT-6 Sol`.
- 4032 wpisy, które napisało 196 fikcyjnych autorów w ciągu 12 tygodni.
- 10 autorów z łukiem, czyli serią wpisów prowadzącą do groźnej sytuacji.
- 2 profile mylące, czyli autorzy piszący rzeczy brzmiące groźnie, ale niegroźne.
- 184 autorów postronnych, niezwiązanych z żadnym łukiem.
- 560 trudnych negatywów: wpisy ostre, ale bez podstawy do zatrzymania, na przykład cytaty z wiadomości, satyra i gniew bez zapowiedzi czynu.

## Porównywane selektory

- **S-rand, ranking losowy.** Układa wpisy w losowej kolejności. Podłoga interpretacyjna: każdy sensowny selektor powinien wypaść lepiej.
- **S0, selektor leksykalny.** Szuka słów i zwrotów z zamrożonej listy, na przykład "jutro", "pójdę", "mam klucze", i liczy z nich wynik ważony.
- **S1, selektor semantyczny.** Porównuje reprezentację wektorową wpisu z krótkimi opisami treści groźnych i zwyczajnych, korzystając z modelu `Qwen3-Embedding-8B`.
- **S3-open, selektor LLM.** Model `Qwen3.8 27B` dostaje reguły decyzyjne z listą sygnałów, które uzasadniają zatrzymanie wpisu.
- **S3', wariant zaślepiony.** Ten sam model, ale bez listy sygnałów, tylko z ogólnym poleceniem. Porównanie z S3-open pokazuje, ile daje jawne określenie kryteriów.
- **S3-com, model kontrolny.** Inny model, `Gemini 3.1 Pro`, uruchomiony na próbie 10 % wpisów. Kontrola względem `Qwen3.8 27B`.

## Wyniki

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

Uwagi:

- Wykryte łuki liczone są z 10, autorzy postronni ze 184. Łuk jest wykryty, gdy co najmniej jeden jego wpis sygnałowy trafi do zbioru zatrzymanego.
- "Sub" oznacza wariant S0, w którym sygnały odrzucenia, takie jak cytat, relacja prasowa czy satyra, obniżają wynik.
- S0 i S1 nie wydają decyzji KEEP, więc dwie ostatnie kolumny są dla nich puste.
- S3-com ocenił tylko próbę 426 wpisów, dlatego jego wyników przy budżetach nie porównujemy z pozostałymi wierszami.
- Wartości to średnie z kilku losowań kolejności wpisów o równym wyniku, stąd ułamki.

## Najważniejsze wnioski

- **Kontrole dodatnie działają.** S0 wykrywa 3 z 4 łuków skoncentrowanych na podstawie samego wpisu, a każdy selektor LLM wykrywa wszystkie 4. Żaden profil mylący nie dostał decyzji KEEP. S-rand przy budżecie 1 % trafia średnio w 0,4 łuku, więc wyniki pozostałych selektorów nie są przypadkiem.
- **Dostęp do historii zwiększa liczbę zatrzymanych autorów postronnych.** Decyzją KEEP S3-open obejmuje 19 autorów postronnych w D0 i 31 w D3-nat, a S3' 30 i 42. To zgodne z hipotezą H4: lepsze rozpoznanie osoby kosztuje zatrzymanie danych innych ludzi.
- **Przy stałym budżecie historia skupia zatrzymanie na mniejszej liczbie osób.** Przy 20 % S3-open zatrzymuje wpisy 160 autorów postronnych w D0 i 109 w D3-nat. Zbiera tyle samo wpisów, ale o mniejszej liczbie ludzi, za to więcej o każdym z nich.
- **Historia pomaga wykryć łuki rozproszone tylko części selektorów.** Decyzją KEEP S3' zatrzymuje 2 łuki rozproszone w D0 i 4 w D3-nat, a S3-com 3 i 4. S3-open zatrzymuje 3 w obu wariantach. Hipoteza H3 potwierdza się więc tylko częściowo.
- **Jawna lista sygnałów ogranicza zbieranie danych.** W D3-nat S3' zatrzymuje decyzją KEEP 84 wpisy, a S3-open 48.
- **W widoku budżetowym selektory LLM wykrywają prawie wszystko od razu.** Przy 5 % znajdują 8 lub 9 łuków w D0 i w D3-nat. Trudne negatywy stanowią 14 % korpusu, więc w tak małym budżecie mieści się wszystko, co odbiega od codziennych tematów. Dlatego w tym widoku historia nie może już niczego dodać.
- **Dwa wyniki trzeba czytać ostrożnie.** Zamrożone opisy, z którymi S1 porównuje wpisy, za bardzo przypominają same łuki; z przemieszanymi opisami S1 wykrywa od 0 do 2 łuków. Agregacja D3-agg premiuje autorów, którzy dużo piszą, a autorzy łuków piszą mniej niż przeciętny autor.
- **Z sześciu kryteriów go / no-go z planu badania dwa są spełnione, trzy nie, a dla jednego nie ustalono progu.** Kryterium 4 wymaga, by S-rand przy 20 % wykrywał najwyżej 1 łuk, co jest nieosiągalne: przy 1 do 5 wpisach sygnałowych na łuk losowanie trafia średnio w około 4 łuki. Kryteria 2 i 5 nie są spełnione z powodu opisanego wyżej nasycenia widoku budżetowego.
- **Wyniki są powtarzalne, a koszt niski.** Dwa niezależne przebiegi S3-open dały te same decyzje dla wszystkich 4032 wpisów. S3-com zgadza się z S3-open w 98 do 99,5 % decyzji. Cały pilotaż kosztował 88,90 USD.

## Uwagi metodologiczne do pełnego badania

1. Autorzy łuków powinni pisać tyle wpisów co pozostali autorzy.
2. Może coś jeszcze?

## Terminologia

- **Łuk skoncentrowany.** Podstawę do zatrzymania widać już w jednym wpisie. Takie łuki są 4.
- **Łuk rozproszony.** Żaden wpis osobno nie daje podstawy do zatrzymania. Widać ją dopiero po zestawieniu kilku wpisów tego samego autora. Takie łuki są 6 i to one są najważniejsze dla badania.
- **Wpis sygnałowy.** Wpis, który niesie część podstawy do zatrzymania. Łuk uznajemy za wykryty, gdy selektor zatrzyma choć jeden jego wpis sygnałowy.
- **Budżet retencyjny.** Część wszystkich wpisów, jaką selektor może zatrzymać: 1 % to 40 wpisów, 5 % to 202, a 20 % to 806. Selektor układa wpisy od najbardziej do najmniej podejrzanych i zatrzymuje tyle z góry listy, ile pozwala budżet.
- **Decyzja KEEP.** Selektory LLM dodatkowo mówią wprost, czy wpis należy zatrzymać do przeglądu przez człowieka (KEEP_FOR_REVIEW), czy odrzucić (DISCARD). To drugi sposób liczenia wyników, niezależny od budżetu.
- **D0.** Selektor widzi tylko oceniany wpis.
- **D3.** Selektor widzi oceniany wpis i wcześniejsze wpisy tego samego autora. W D3-nat model językowy dostaje tę historię wprost, w D3-txt historia trafia do jednego okna modelu wektorowego, a D3-agg nie pokazuje historii, tylko sumuje trzy najwyższe wyniki wpisów autora.

# EP-SKEL WYNIKI 2026-10-28

## Koncept

Symulujemy automatyczny selektor, który przegląda wpisy w mediach społecznościowych i decyduje, które zachować do dalszej analizy. Interesują nas dwie rzeczy: ile groźnych sytuacji selektor wykrywa i ilu niezwiązanych z nimi osób dane przy tym zatrzymuje. Główne pytanie brzmi: czy selektor, który oprócz pojedynczego wpisu widzi też wcześniejsze wpisy tego samego autora, wykrywa więcej.

## Hipotezy

Wzięte z planu badania (sekcja 2).

- **H1.** Krzywa wykrywalności nasyca się przy budżecie retencyjnym istotnie niższym niż 100 %.
- **H2.** Przy równym budżecie retencyjnym selektor LLM ma wyższą wykrywalność niż selektor leksykalny, ale gorszą gradację rankingu (liczne remisy nie występują tylko u S0).
- **H3.** Wykrywalność łuków o sygnale rozproszonym rośnie skokowo przy przejściu z dostępu do pojedynczego wpisu (D0) na dostęp do historii autora (D3); dla łuków skoncentrowanych przyrost jest marginalny.
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

### Widok budżetowy

Selektor układa wszystkie wpisy od najbardziej podejrzanych i zatrzymuje górne 1 %, 5 % lub 20 %.

| Selektor | Dostęp | Łuki, 1 % | Łuki, 5 % | Łuki, 20 % | Rozproszone, 20 % | Postronni, 20 % |
|---|---|---|---|---|---|---|
| S-rand | D0 | 0,4 | 1,6 | 4,6 | 3,6 | 178 |
| S0 | D0 | 2,0 | 3,7 | 9,0 | 6,0 | 177 |
| S0 | D3-agg | 0,0 | 0,0 | 3,7 | 2,7 | 88 |
| S1 | D0 | 4 | 8 | 9 | 5 | 179 |
| S1 | D3-txt | 0 | 2 | 5 | 3 | 126 |
| S3-open | D0 | 7 | 8 | 10 | 6 | 160 |
| S3-open | D3-nat | 7 | 9 | 10 | 6 | 109 |
| S3' | D0 | 6 | 8 | 10 | 6 | 154 |
| S3' | D3-nat | 6 | 8 | 10 | 6 | 104 |

- **Łuki:** liczba wykrytych łuków z 10. Łuk jest wykryty, gdy co najmniej jeden jego wpis sygnałowy trafi do zbioru zatrzymanego.
- **Rozproszone:** liczba wykrytych łuków rozproszonych z 6.
- **Postronni:** liczba autorów postronnych, ze 184, których co najmniej jeden wpis został zatrzymany.
- S0 to wariant "sub", w którym sygnały odrzucenia, takie jak cytat, relacja prasowa czy satyra, obniżają wynik.
- Wartości to średnie z kilku losowań kolejności wpisów o równym wyniku, stąd ułamki.
- S3-com nie występuje w tej tabeli, bo ocenił tylko próbę 426 wpisów i jego wyników przy budżetach nie da się porównać z resztą.

### Widok decyzyjny

Selektory LLM dodatkowo decydują o każdym wpisie: KEEP_FOR_REVIEW albo DISCARD. Ten widok nie zależy od budżetu.
S0 i S1 nie wydają takich decyzji, więc ich tu nie ma.

| Selektor | Dostęp | Łuki z KEEP | W tym rozproszone | Postronni z KEEP |
|---|---|---|---|---|
| S3-open | D0 | 7 | 3 | 19 |
| S3-open | D3-nat | 7 | 3 | 31 |
| S3' | D0 | 6 | 2 | 30 |
| S3' | D3-nat | 8 | 4 | 42 |
| S3-com, próba 10 % | D0 | 7 | 3 | 1 |
| S3-com, próba 10 % | D3-nat | 8 | 4 | 1 |

- **Łuki z KEEP:** liczba łuków, z 10, w których co najmniej jeden wpis sygnałowy dostał decyzję KEEP.
- **Postronni z KEEP:** liczba autorów postronnych, z co najmniej jednym wpisem z decyzją KEEP.
- S3-com ocenił próbę 426 wpisów, w tym wszystkie wpisy sygnałowe, więc jego liczba łuków jest porównywalna z innymi wierszami, a liczba postronnych nie.

## Najważniejsze wnioski

- **Kontrole dodatnie działają.** S0 wykrywa 3 z 4 łuków skoncentrowanych na podstawie samego wpisu, a każdy selektor LLM wykrywa wszystkie 4. Żaden profil mylący nie dostał decyzji KEEP. S-rand przy budżecie 1 % trafia średnio w 0,4 łuku, więc wyniki pozostałych selektorów nie są przypadkiem.
- **Dostęp do historii zwiększa liczbę zatrzymanych autorów postronnych.** Decyzją KEEP S3-open obejmuje 19 autorów postronnych w D0 i 31 w D3-nat, a S3' 30 i 42. To zgodne z hipotezą H4: lepsze rozpoznanie osoby kosztuje zatrzymanie danych innych ludzi.
- **Przy stałym budżecie historia skupia zatrzymanie na mniejszej liczbie osób.** Przy 20 % S3-open zatrzymuje wpisy 160 autorów postronnych w D0 i 109 w D3-nat. Zbiera tyle samo wpisów, ale o mniejszej liczbie ludzi, za to więcej o każdym z nich.
- **Historia pomaga wykryć łuki rozproszone tylko części selektorów.** Decyzją KEEP S3' zatrzymuje 2 łuki rozproszone w D0 i 4 w D3-nat, a S3-com 3 i 4. S3-open zatrzymuje 3 w obu wariantach. Hipoteza H3 potwierdza się więc tylko częściowo.
- **Jawna lista sygnałów ogranicza zbieranie danych.** W D3-nat S3' zatrzymuje decyzją KEEP 84 wpisy, a S3-open 48.
- **W widoku budżetowym selektory LLM wykrywają prawie wszystko od razu.** Przy 5 % znajdują 8 lub 9 łuków w D0 i w D3-nat. Trudne negatywy stanowią 14 % korpusu, więc w tak małym budżecie mieści się wszystko, co odbiega od codziennych tematów. Dlatego w tym widoku historia nie może już niczego dodać.
- **Dwa wyniki trzeba czytać ostrożnie.** Zamrożone opisy, z którymi S1 porównuje wpisy, za bardzo przypominają same łuki; z przemieszanymi opisami S1 wykrywa od 0 do 2 łuków. Agregacja D3-agg premiuje autorów, którzy dużo piszą, a autorzy łuków piszą mniej niż przeciętny autor.
- **Z sześciu kryteriów go / no-go z planu badania dwa są spełnione, trzy nie, a dla jednego nie ustalono progu.** Kryterium 4 wymaga, by S-rand przy 20 % wykrywał najwyżej 1 łuk, co jest nieosiągalne: przy 1 do 5 wpisach sygnałowych na łuk losowanie trafia średnio w około 4 łuki. Kryteria 2 i 5 nie są spełnione z powodu opisanego wyżej nasycenia widoku budżetowego.
- **Wyniki są powtarzalne.** Dwa niezależne przebiegi S3-open dały te same decyzje dla wszystkich 4032 wpisów. S3-com zgadza się z S3-open w 98 do 99,5 % decyzji.

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

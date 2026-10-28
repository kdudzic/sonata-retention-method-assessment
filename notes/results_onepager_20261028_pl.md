# EP-SKEL: wyniki pilotażu

## O co chodzi w badaniu

Badanie sprawdza, czy sztuczna inteligencja naprawdę pozwala służbom zbierać mniej danych o ludziach. Symulujemy
automatyczny filtr, który przegląda wpisy w mediach społecznościowych i decyduje, które zachować do dalszej
analizy. Interesują nas dwie rzeczy: ile groźnych sytuacji filtr wykrywa i ile przy tym zatrzymuje danych osób
niewinnych. Główne pytanie brzmi: czy filtr, który oprócz pojedynczego wpisu widzi też wcześniejsze wpisy tej
samej osoby, wykrywa więcej, i jaką cenę płacą za to osoby postronne.

Pilotaż prowadziliśmy na sztucznie wygenerowanym, polskim korpusie, w którym z góry wiadomo, kto jest celem:

- 4032 wpisy, które napisało 196 fikcyjnych autorów w ciągu 12 tygodni;
- 10 autorów z "łukiem", czyli serią wpisów prowadzącą do groźnej sytuacji;
- 2 autorów "mylących", którzy piszą rzeczy brzmiące groźnie, ale niegroźne;
- 184 zwykłych autorów, czyli osoby postronne;
- 560 wpisów to "trudne przypadki": ostre, ale dopuszczalne, na przykład cytaty z wiadomości, satyra i gniew bez
  zapowiedzi czynu.

## Najważniejsze pojęcia

- **Łuk skoncentrowany.** Groźbę widać już w jednym wpisie. Takie łuki są 4.
- **Łuk rozproszony.** Żaden wpis osobno nie jest groźny. Zagrożenie widać dopiero po zestawieniu kilku wpisów
  tej samej osoby. Takie łuki są 6 i to one są najważniejsze dla badania.
- **Wpis sygnałowy.** Wpis, który niesie część zagrożenia. Łuk uznajemy za wykryty, gdy filtr zatrzyma choć jeden
  jego wpis sygnałowy.
- **Budżet.** Część wszystkich wpisów, jaką filtr może zatrzymać: 1 % to 40 wpisów, 5 % to 202, a 20 % to 806.
  Filtr układa wpisy od najbardziej do najmniej podejrzanych i zatrzymuje tyle z góry listy, ile pozwala budżet.
- **Decyzja "zatrzymaj".** Filtry oparte na modelach językowych dodatkowo mówią wprost, czy dany wpis warto
  zatrzymać. To drugi sposób liczenia wyników, niezależny od budżetu.
- **Sam wpis albo wpis z historią.** Filtr widzi albo tylko oceniany wpis, albo także wcześniejsze wpisy tej
  samej osoby.

## Porównywane filtry

- **Losowy.** Wybiera wpisy na chybił trafił. To punkt odniesienia: każdy sensowny filtr powinien być lepszy.
- **Lista słów.** Szuka słów i zwrotów typu "jutro", "pójdę", "mam klucze". Tak działają klasyczne filtry, do
  których odnosi się dzisiejsze prawo.
- **Podobieństwo znaczeń.** Porównuje treść wpisu z krótkimi opisami groźnych i zwyczajnych wypowiedzi, korzystając
  z modelu Qwen3-Embedding-8B.
- **Model językowy z listą kryteriów.** Model Qwen3.8 27B dostaje reguły, które mówią, co uzasadnia zatrzymanie
  wpisu, na przykład własną zapowiedź działania, wskazany cel i bliski termin.
- **Model językowy bez listy kryteriów.** Ten sam model, ale tylko z ogólnym poleceniem. Porównanie obu wariantów
  pokazuje, ile daje precyzyjne wskazanie, czego szukać.
- **Model kontrolny.** Inny model, Gemini 3.1 Pro, sprawdzony na 10 % wpisów, żeby wiedzieć, czy wynik nie zależy
  od jednego modelu.

## Wyniki

| Filtr | Co widzi | Wykryte łuki (z 10) przy budżecie 1 % / 5 % / 20 % | Osoby postronne zatrzymane przy budżecie 20 % (ze 184) | Łuki z decyzją "zatrzymaj", w tym rozproszone | Osoby postronne z decyzją "zatrzymaj" |
|---|---|---|---|---|---|
| Losowy | sam wpis | 0,4 / 1,6 / 4,6 | 178 | nie dotyczy | nie dotyczy |
| Lista słów | sam wpis | 2 / 3,7 / 9 | 177 | nie dotyczy | nie dotyczy |
| Lista słów | wpis z historią | 0 / 0 / 3,7 | 88 | nie dotyczy | nie dotyczy |
| Podobieństwo znaczeń | sam wpis | 4 / 8 / 9 | 179 | nie dotyczy | nie dotyczy |
| Podobieństwo znaczeń | wpis z historią | 0 / 2 / 5 | 126 | nie dotyczy | nie dotyczy |
| Model z listą kryteriów | sam wpis | 7 / 8 / 10 | 160 | 7, w tym 3 | 19 |
| Model z listą kryteriów | wpis z historią | 7 / 9 / 10 | 109 | 7, w tym 3 | 31 |
| Model bez listy kryteriów | sam wpis | 6 / 8 / 10 | 154 | 6, w tym 2 | 30 |
| Model bez listy kryteriów | wpis z historią | 6 / 8 / 10 | 104 | 8, w tym 4 | 42 |
| Model kontrolny, 10 % wpisów | sam wpis | nie dotyczy | nie dotyczy | 7, w tym 3 | 1 |
| Model kontrolny, 10 % wpisów | wpis z historią | nie dotyczy | nie dotyczy | 8, w tym 4 | 1 |

Lista słów i podobieństwo znaczeń nie wydają decyzji "zatrzymaj", więc dwie ostatnie kolumny ich nie dotyczą. Model
kontrolny ocenił tylko próbę wpisów, dlatego jego wyników przy budżetach nie porównujemy z resztą. Ułamki biorą się
z uśredniania kilku losowań tam, gdzie wpisy mają równy wynik.

## Najważniejsze wnioski

- **Konstrukcja badania działa.** Wszystkie 4 łuki skoncentrowane wykrywa każdy model językowy, a 3 z nich także
  sama lista słów. Żaden z 2 autorów mylących nie dostał decyzji "zatrzymaj". Filtr losowy przy budżecie 1 % trafia
  średnio w 0,4 łuku, więc wyniki pozostałych filtrów nie są przypadkiem.
- **Dostęp do historii zwiększa liczbę zatrzymanych osób niewinnych.** Model z listą kryteriów decyzją "zatrzymaj"
  obejmuje 19 osób postronnych bez historii i 31 z historią. Model bez listy: 30 i 42. To potwierdza drugą część
  tezy badania: lepsze rozpoznanie osoby kosztuje więcej danych o innych.
- **Przy stałym budżecie historia skupia zatrzymanie na mniejszej liczbie osób.** Przy 20 % model z listą
  zatrzymuje wpisy 160 osób postronnych bez historii, a 109 z historią. Zbiera tyle samo danych, ale o mniejszej
  liczbie ludzi, za to głębiej o każdym z nich.
- **Historia pomaga wykryć łuki rozproszone tylko części modeli.** Model bez listy kryteriów zatrzymuje 2 łuki
  rozproszone bez historii i 4 z historią, model kontrolny 3 i 4. Model z listą zatrzymuje 3 w obu wariantach.
- **Lista kryteriów hamuje model.** Z historią model bez listy kryteriów zatrzymuje 84 wpisy, a model z listą 48.
  Precyzyjne określenie, czego szukać, ogranicza zbieranie danych.
- **Przy budżetach modele wykrywają prawie wszystko od razu.** Przy 5 % znajdują 8 lub 9 łuków z historią i bez.
  W korpusie jest 14 % ostrych, choć dopuszczalnych wpisów, więc w tak małym budżecie mieści się wszystko, co
  odbiega od codziennych tematów. Dlatego przy budżetach historia nie może już niczego dodać.
- **Dwa wyniki trzeba czytać ostrożnie.** Opisy używane przez filtr podobieństwa znaczeń za bardzo przypominają
  same łuki; z przemieszanymi opisami ten filtr wykrywa od 0 do 2 łuków. Sumowanie wyników z historii premiuje
  osoby, które piszą dużo, a autorzy łuków piszą mniej niż przeciętny autor.
- **Plan badania zakładał sześć warunków przejścia do pełnej skali.** Dwa są spełnione, trzy nie, a dla jednego
  nie ustalono progu. Jeden z niespełnionych warunków jest nieosiągalny w tej konstrukcji: wymaga, by filtr losowy
  przy 20 % trafiał najwyżej w 1 łuk, a przy kilku wpisach sygnałowych na łuk losowanie trafia średnio w około 4.
  Dwa pozostałe nie są spełnione z powodu opisanego wyżej wykrywania prawie wszystkiego naraz.
- **Wyniki są powtarzalne, a koszt niski.** Dwa niezależne przebiegi tego samego modelu dały te same decyzje we
  wszystkich 4032 wpisach. Model kontrolny zgadza się z głównym w 98 do 99,5 % decyzji. Cały pilotaż kosztował
  88,90 USD.

## Co zmienić przed badaniem w pełnej skali

1. Autorzy łuków powinni pisać tyle wpisów co pozostali autorzy.
2. Opisy dla filtra podobieństwa znaczeń powinien napisać ktoś, kto nie zna łuków, wyłącznie na podstawie reguł.
3. Budżety trzeba dobrać tak, żeby nie mieściły od razu wszystkich ostrych wpisów.
4. Wyniki oparte na decyzji "zatrzymaj" warto raportować obok wyników przy budżetach jako miarę główną.

Pełny raport techniczny (po angielsku): `notes/results_report_20261027.md`.

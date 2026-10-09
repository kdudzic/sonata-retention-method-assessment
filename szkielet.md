# NCN SONATA plan szkieletu (2026-08-24)

## 0. Rozmiar szkieletu

| Pole | Rozmiar |
|---|---|
| Wpisy | 4 000 |
| Autorzy | 200 |
| Łuki | 10 |
| Podział etykiet | 84%-13%-3% |
| Budżety | gł. 5% i 20% |

## 1. Eksploracja istniejących korpusów

Wymogi:

- Korpus pochodzenia ludzkiego.
- Szeroki zakres tematyczny, naturalny język.
- Łuki (etykietowanie użytkowników).

Propozycje:

- [PANDORA](https://aclanthology.org/2021.socialnlp-1.12.pdf) oraz [TwiBot-22](https://arxiv.org/pdf/2206.04564) to fajne zbiory podchodzące strukturą pod badanie, ale trudno jest uzyskać do nich dostęp.
- Zamiast tego mamy dwa zbiory danych zescrapowanych postów z BlueSky: [bluesky-posts](https://huggingface.co/datasets/withalim/bluesky-posts) oraz [bluesky](https://huggingface.co/datasets/Roronotalt/bluesky).

## 2. Utworzenie ręcznie łuków przypadków celowych

Element łuków stworzony ręcznie przez Marcina. Potem rozbudowujemy syntetycznie tymi samym modelem, co w 3.

## 3. Utworzenie datasetu dla szkieletu

Dwie opcje:

- Filtracja istniejącego zbioru.
  - Wymagany obszerny pre-processing pod nasze potrzeby.
- Generacja syntetyczna.
  - Wymagane zbadanie technik dywersyfikacji generacji oraz potencjalnie kontrolowalności - **już na tym etapie**.
  - Proponowany model: `Fable 5` lub `GPT-5.6 Sol`. Nie ma co się tutaj ograniczać, weźmiemy najlepszy z możliwych poprzez OpenRouter.

## 4. Ustalenie metryk ewaluacyjnych

Zasadniczo mogą być te z dokumentu, kopiuję je poniżej. Tutaj pytanie do Marcina i Dominiki - co rzeczywiście **chcecie** zobaczyć i wykazać?

Metryki:

- Wykrywalność — ile z 10 (potem ~30) łuków trafiło do zbioru zatrzymanego (detected_arcs@k, definicja ścisła; luźna dodatkowo).
- Inwazyjność — liczba niepowiązanych autorów zatrzymanych na jeden wykryty łuk (BPD@k); dodatkowo profile_depth — ile wpisów na jednego niewinnego autora zatrzymano (głębokość profilu).

## 5. Wstępne eksperymenty na wybranych metodach

5.1. Selektor leksykalny:

- Potrzebujemy listy termów z wagami (zgodnie z ostatnim planem to zadanie Marcina).

5.2. Selektor semantyczny:

- W ramach szkieletu robimy tylko 2a.
- Trzeba wybrać dobry model do embeddingów.
  - Propozycja: `Qwen/Qwen3-Embedding-8B`.

5.3. LLM:

- Trzeba dobrać dobry model. Nasze wymogi:
  - Open-source.
  - Near-SOTA.
  - Hostowalny na infrastrukturze CSI bez blokowania wszystkich GPU na dłużej.
  - Propozycje:
    - `DeepSeek V4 Flash` / `Pro`.
    - `GLM-5.2`.
    - `Inkling`.
    - `Kimi K3`.
    - `Qwen3.8 27B` / `Max`.

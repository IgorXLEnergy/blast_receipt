# Demo na Vercel

Statyczne demo dwóch rzeczywistych testów OCR. Nie uruchamia PaddleOCR, nie
analizuje nowych zdjęć i nie wymaga backendu. Zapisane odczyty OCR są przetwarzane
przez aktualny parser podczas przygotowania pliku `data.json`, a nie podczas
wizyty na stronie. Potwierdzone ręcznie produkty są wyświetlane osobno.

## Publikacja

1. W Vercel wybierz **Add New → Project** i zaimportuj
   `IgorXLEnergy/blast_receipt` z GitHuba.
2. Root Directory: katalog główny repozytorium. Framework Preset: **Other**.
3. Konfigurację pobiera `vercel.json`: Build Command `sh demo/build.sh`,
   Output Directory `demo/dist`. Nie są potrzebne zmienne środowiskowe ani API.
4. Kliknij **Deploy**. Vercel wygeneruje adres demo. Przy podłączonej gałęzi
   `main` kolejne pushe mogą automatycznie aktualizować stronę.

Konfiguracja Vercela służy do tego demo. Pełne API OCR nadal uruchamia się
lokalnie/chmurowo zgodnie z głównym README.

## Lokalne sprawdzenie

```bash
sh demo/build.sh
python3 -m http.server 8090 --directory demo/dist
```

Otwórz na swoim komputerze `http://localhost:8090`. Wybierz oba przykłady.
Przełączanie działa natychmiast na zapisanych danych; strona nie wysyła zdjęć.

## Odświeżanie zapisanych wyników

Po zmianie parsera lub anonimowych danych testowych:

```bash
python3 demo/export_results.py
sh demo/build.sh
```

Zapisz zaktualizowany `demo/data.json` w Git. Budowanie na Vercelu kopiuje gotowe
pliki i nie wymaga Python/PaddleOCR. Surowe zdjęcia, adresy, NIP-y i identyfikatory
transakcji nie są częścią demo; źródłem są anonimowe fixtures z `service/tests`.

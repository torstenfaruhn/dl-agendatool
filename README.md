# DL Agendatool – XML naar Cue Print, TXT naar Cue Web

Deze repository is een aanpassing van **`20261021 0935 dl-agendatool-dubbele-verwijderd.zip`**, met de bestaande TXT-export behouden. De tweede export is gecorrigeerd: het bronbestand voor **Cue Web is een getagd `.txt`-bestand**, geen XML.

## Twee afzonderlijke functies

| Knop | Invoer | Uitvoer | Werking |
| --- | --- | --- | --- |
| **XML > Cue Print** | Umbraco-agenda `.xml` | `agenda_export.txt` | Bestaande export met tags voor Cue Codefixer |
| **TXT > Cue Web** | Getagde agenda `.txt`, bijvoorbeeld `20261014 agenda zuid.txt` | `agenda_export.docx` | Vervangt de tags door echte Word-opmaak |

### XML > Cue Print

1. Lees de evenementen uit de XML en pas de bestaande normalisatie toe.
2. Verwijder exacte duplicaten volgens **optie A**: verwerkte plaatsnaam, genre en volledige verwerkte tekst zijn identiek.
3. Sorteer plaatsen alfabetisch zonder onderscheid tussen hoofdletters en kleine letters. Binnen een plaats blijft de oorspronkelijke volgorde behouden.
4. Maak de `.txt` met de bestaande Cue Print-tags.

**De oorspronkelijke XML-verwerking is niet gewijzigd.**

### TXT > Cue Web

1. Upload een **bestaand getagd TXT-bestand**. Je kunt hiervoor ook de uitvoer van de eerste functie gebruiken.
2. De omzetter leest de plaatsblokken (`<l_region>`) en berichtblokken (`<l_info>` of `<l_info(1)>`). Ook `<bold>`, de genummerde variant `<bold(1)>`, `<SU>`, `<EP>` en `<extra_leading>` worden verwerkt. De bijbehorende sluit-tags moeten overeenkomen.
3. Opmaak volgens het aangeleverde `voorbeeld agenda naar word.docx`:
   - Plaatsnaam: eigen alinea, **vet en in hoofdletters**.
   - Vet gemarkeerde evenementtitel: **vet**.
   - Overige berichttekst: gewone tekst op dezelfde regel als de titel, gescheiden door een spatie.
   - Regels die in de TXT midden in een bericht zijn afgebroken, worden doorlopend weergegeven.
4. Wanneer binnen één `<l_info>`-blok meer dan één vet gemarkeerde titel staat, wordt elke titel met de bijbehorende tekst een apart agendabericht.
5. Download het `.docx`-bestand of kopieer de opgemaakte tekst. Het kopiëren van vetopmaak hangt af van de browser; het gedownloade Word-document bevat de opmaak altijd.

**Belangrijk:** de TXT-naar-Word-omzetter **verandert de inhoud of volgorde van het bronbestand niet**. Een plaats die op verschillende plekken in de TXT staat, kan daarom ook meerdere keren voorkomen in Word. Ook identieke berichten blijven staan als ze al dubbel in het aangeleverde TXT-bestand staan. Als het TXT-bestand door de eerste functie is gemaakt, zijn de eerdere XML-dubbelen daar al uitgehaald en zijn plaatsen al gesorteerd.

De omzetter slaat lege plaats- en berichtblokken over. Onvolledige/ongeldige tags geven een foutmelding (`ERR_TXT_FORMAT`) in plaats van stille gegevensverliezen. `.txt` wordt als UTF-8 (met of zonder BOM) gelezen, met Windows-1252 als terugvaloptie.

## Lokaal starten en testen

Vereisten: Python, pip en een browser. `python-docx` schrijft Word-documenten; Flask is de webserver en gunicorn start de app op Render.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Open `http://localhost:5000` in een browser.

## Repository bijwerken op GitHub

1. Maak zo nodig eerst een back-up of branch van de bestaande repository.
2. Pak de gedownloade ZIP uit. Kopieer **de inhoud van `dl-agendatool/`** naar de bestaande projectmap waarin `app.py` staat.
3. Vervang de gewijzigde bestanden en behoud de bestaande `.git`-map. Verwijder geen andere projectbestanden zonder ze te controleren.
4. Test lokaal met de commando's hierboven.
5. Commit en push naar de branch die met Render is verbonden (hieronder als `main` aangeduid).

```bash
git add .
git commit -m "Ondersteun genummerde vet-tags in TXT naar Word"
git push origin main
```

## Render (bestaande Web Service)

Geen extra Render-service nodig. De instellingen zijn:

- **Type:** Web Service; **runtime:** Python.
- **Repository en branch:** de bestaande GitHub-repo en de gekoppelde branch (`main` als dit de ingestelde branch is).
- **Root directory:** projectroot met `app.py` en `requirements.txt`.
- **Build command:** `pip install -r requirements.txt`.
- **Start command:** `gunicorn app:app`.
- **Package manager:** pip.
- **Pythonversie:** uit `runtime.txt`.
- **Sleutels/variabelen:** geen API-sleutels nodig.

`render.yaml` bevat de Web Service-configuratie.

### Praktijkcontrole na de deployment

1. Upload een XML-bestand bij **XML > Cue Print**. Controleer `.txt`, optie A en alfabetische plaatsvolgorde.
2. Upload **`20261014 agenda noord.txt`** bij **TXT > Cue Web**. Controleer dat het bericht “Greatest hits 1 and more - Queen Must Go On” vet is opgemaakt en dat meerdere titels in hetzelfde `<l_info>`-blok apart verschijnen.
3. Upload ook **`20261014 agenda zuid.txt`** bij **TXT > Cue Web** om te controleren of de vorige export correct blijft.
4. Controleer de eerste twee plaatsblokken (Bunde, Eijsden) met `voorbeeld agenda naar word.docx`.
5. Controleer een bericht zonder `<SU>`, een blok met `<l_info(1)>` en de mobiele weergave.
6. Controleer foutmeldingen voor een verkeerd bestandstype en kapotte tags.

## Beveiliging en beperkingen

- Maximaal 5 MB per upload; voor elke functie wordt de juiste extensie (`.xml` respectievelijk `.txt`) gecontroleerd.
- De verwerking gebeurt in het geheugen; de app schrijft de geüploade gegevens niet weg.
- Geen tracking, analytics of externe browserscripts.
- Een Content Security Policy (CSP) en extra beveiligingsheaders zijn ingesteld.
- Geen logging van berichtteksten of persoonsgegevens: gebruikersmeldingen bevatten alleen een foutomschrijving en technische foutcode.
- Een ongeldige TXT-structuur wordt geweigerd. De ondersteuning is bedoeld voor het aangeleverde Cue Print-tagformaat, niet voor willekeurige platte TXT-bestanden.

De 23 automatische verwerkingstests zijn geslaagd. Beide aangeleverde TXT-voorbeelden zijn opnieuw omgezet: **Noord: 52 berichten in 19 gevulde plaatsblokken; Zuid: 68 berichten in 37 gevulde plaatsblokken**. De volledige Flask-browsertest kon niet worden uitgevoerd omdat Flask in de bouwomgeving niet beschikbaar was; controleer daarom de uploadknoppen na het uitrollen.

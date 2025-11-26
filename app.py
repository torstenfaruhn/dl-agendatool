# app.py - Flask webapp for XML agenda -> text export
# Generated for deployment on Render.com

from flask import Flask, render_template, request
from io import StringIO

# === Transformatielogica uit het Colab-notebook ===
# Transformatiefunctie met verbeterde datum- en tijdlogica
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

MONTHS = [
    "januari","februari","maart","april","mei","juni",
    "juli","augustus","september","oktober","november","december"
]
MONTH_INDEX = {m: i+1 for i, m in enumerate(MONTHS)}

def normalize_place_name(t: str) -> str:
    if not t:
        return ''
    t = t.strip()
    repl = [
        (r"\bUrmond\s+Gemeente\s+Stein\b", "Urmond"),
        (r"\bValkenburg\s+aan\s+de\s+Geul\b", "Valkenburg"),
        (r"\bValkenburg\s+a/d\s+Geul\b", "Valkenburg"),
        (r"\bElsoo\s+Lb\b", "Elsloo"),
        (r"\bGemeente\s+Stein\b", "Stein"),
    ]
    for p, r in repl:
        t = re.sub(p, r, t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def normalize_postcodes(t: str) -> str:
    if not t:
        return t
    return re.sub(r"\b(\d{4})\s*([A-Za-z]{2})\b",
                  lambda m: f"{m.group(1)} {m.group(2).upper()}", t)

def normalize_housenumbers(t: str) -> str:
    if not t:
        return t
    return re.sub(r"\b(\d+)\s*([A-Za-z])\b",
                  lambda m: f"{int(m.group(1))}{m.group(2).lower()}", t)

def normalize_times(t: str) -> str:
    """Implementeert regel 13, zonder minuten aan te passen of dubbele .00 te maken."""
    if not t:
        return t
    # Verwijder spaties na '.' in tijd-achtige patronen: 10. 00 -> 10.00, 15. 35 -> 15.35
    t = re.sub(r"(\d{1,2})\.\s*(\d{2})", r"\1.\2", t)
    # 10-14.30 uur -> 10.00-14.30 uur (alleen als eerste deel een uur is 0-23)
    t = re.sub(r"(?<!\.)\b([01]?\d|2[0-3])-(\d{1,2}\.\d{2})\s*uur\b",
              lambda m: f"{int(m.group(1))}.00-{m.group(2)} uur", t)
    # 8-10 uur -> 8.00-10.00 uur
    t = re.sub(r"(?<!\.)\b([01]?\d|2[0-3])-(\d{1,2})\s*uur\b",
              lambda m: f"{int(m.group(1))}.00-{int(m.group(2))}.00 uur", t)
    # 9 uur -> 9.00 uur (en alleen uren 0-23, niet '35 uur' in 15.35 uur)
    t = re.sub(r"(?<!\.)\b([01]?\d|2[0-3])\s*uur\b",
              lambda m: f"{int(m.group(1))}.00 uur", t)
    # 12u -> 12.00 uur
    t = re.sub(r"(?<!\.)\b([01]?\d|2[0-3])u\b",
              lambda m: f"{int(m.group(1))}.00 uur", t)
    return t

def simplify_date_ranges(t: str) -> str:
    """Implementeert regels 11 en 12.

    - Herken datumbereiken "datum1 ... tot/t/m datum2" en maak er
      "* t/m [datum2] *" of "* t/m [weekday datum2]" van.
    - Ondersteunt zowel maandnamen als numerieke datums met weekdag.
    """
    if not t:
        return t

    # 1) Numerieke datums met weekdag en tijden, zoals:
    #    * zo 22-6 * 14.00 uur tot zo 13-7 * 18.00 uur
    weekday_pattern = r"(?:ma|di|wo|do|vr|za|zo)"

    def repl_numeric(m):
        wd2 = m.group(1)
        date2 = m.group(2)
        return f"* t/m {wd2} {date2} "

    numeric_pat = (
        rf"\*\s*{weekday_pattern}\s+\d{{1,2}}-\d{{1,2}}\s*"  # * zo 22-6
        rf"\*\s*[^*]*?(?:tot|t/m)\s*"                        # * 14.00 uur tot
        rf"({weekday_pattern})\s+(\d{{1,2}}-\d{{1,2}})"      # zo 13-7
        rf"\s*\*[^*]*"                                       # * 18.00 uur
    )

    t = re.sub(numeric_pat, repl_numeric, t, flags=re.IGNORECASE)

    # 2) Variant met maandnamen, zoals: 22 juni tot 13 juli
    months_pattern = "|".join(MONTHS)
    pat = (
        rf"(\d{{1,2}})\s+({months_pattern})(?:\s+(\d{{2,4}}))?"  # dag1 maand1 [jaar1]
        rf"\s+(?:tot|t/m)\s+"                                     # tot / t/m
        rf"(\d{{1,2}})\s+({months_pattern})(?:\s+(\d{{2,4}}))?"  # dag2 maand2 [jaar2]
    )

    def repl_month(m):
        day1 = m.group(1)
        month1 = m.group(2)
        year1 = m.group(3)
        day2 = m.group(4)
        month2 = m.group(5)
        year2 = m.group(6)

        date2_str = f"{day2} {month2}"
        if year2:
            date2_str = f"{date2_str} {year2}"
        else:
            m1_idx = MONTH_INDEX.get(month1.lower(), None)
            m2_idx = MONTH_INDEX.get(month2.lower(), None)
            if m1_idx is not None and m2_idx is not None and m2_idx < m1_idx:
                # Cross-jaar: -26 toevoegen zoals beschreven
                date2_str = f"{date2_str} -26"

        return f"* t/m {date2_str} *"

    t = re.sub(pat, repl_month, t, flags=re.IGNORECASE)
    return t

def normalize_spaces_and_punctuation(t: str) -> str:
    """Regel 14: spaties rond leestekens normaliseren, maar **zonder** tijden te breken.
    We laten de punt (.) met rust; die is belangrijk voor tijden en decimalen.
    """
    if not t:
        return t
    # Verwijder dubbele spaties
    t = re.sub(r"\s+", " ", t)
    # Behandel alleen , ; : ! ?
    t = re.sub(r"\s+([,;:!?])", r"\1", t)
    t = re.sub(r"([,;:!?])(\S)", r"\1 \2", t)
    return t.strip()

def strip_trailing_asterisk(t: str) -> str:
    if not t:
        return t
    t = t.rstrip()
    while t.endswith('*'):
        t = t[:-1].rstrip()
    return t

def process_su_text(t: str) -> str:
    """Volgorde van bewerkingen volgens de regels, zodat ze elkaar niet in de weg zitten.

    8. postcodes
    9. huisnummers
    10. plaatsnamen
    11/12. datumbereiken
    13. tijdstippen
    14. spaties en leestekens
    17. trailing '*'
    """
    if t is None:
        t = ""
    t = normalize_postcodes(t)
    t = normalize_housenumbers(t)
    t = normalize_place_name(t)
    t = simplify_date_ranges(t)
    t = normalize_times(t)
    t = normalize_spaces_and_punctuation(t)
    t = strip_trailing_asterisk(t)
    return t

def transform_xml(xml_input: str) -> str:
    """Verwerk input-XML en geef tekst terug met `<EP>` en `<SU>` alleen als opentags."""
    root = ET.fromstring(xml_input)
    ev_by_place = defaultdict(list)

    for e in root.iter():
        if e.tag != "evenement":
            continue
        p = e.find("plaats")
        g = e.find("genre")
        t = e.find("tekst")
        if p is None or g is None or t is None:
            continue
        pn = normalize_place_name((p.text or '').strip())
        gn = (g.text or '').strip()
        su = process_su_text((t.text or '').strip())
        ev_by_place[pn].append({"plaats": pn, "genre": gn, "su": su})

    # Bouw de output handmatig als tekst, zodat we zelf bepalen welke tags
    # wel en niet gesloten worden.
    lines = []
    lines.append("<body>")

    for place in sorted(ev_by_place.keys(), key=lambda s: s.lower()):
        lines.append(f"<l_region>{place}</l_region>")
        for ev in ev_by_place[place]:
            lines.append("<EP>")
            lines.append("<l_info>")
            lines.append(f"<bold>{ev['genre']}</bold>")
            # SU opentag zonder sluit-tag, conform jouw wens
            lines.append(f"<SU>{ev['su']}")
            lines.append("</l_info>")

    lines.append("</body>")
    print("transform_xml geladen met verbeterde datums en tijden.")
    return "\n".join(lines)

print("Functies geladen.")

# Maak Flask-app
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    output_text = None
    error = None

    if request.method == "POST":
        upload = request.files.get("xml_file")
        if not upload or upload.filename == "":
            error = "Geen XML-bestand geselecteerd."
        else:
            # Probeer UTF-8, val desnoods terug op Latin-1
            raw = upload.read()
            try:
                xml_input = raw.decode("utf-8")
            except UnicodeDecodeError:
                xml_input = raw.decode("latin-1", errors="ignore")

            try:
                output_text = transform_xml(xml_input)
            except Exception as exc:  # pragma: no cover
                error = f"Er ging iets mis bij het verwerken van het bestand: {exc}"

    return render_template("index.html", output_text=output_text, error=error)

if __name__ == "__main__":
    # Voor lokaal testen (Render gebruikt gunicorn)
    app.run(host="0.0.0.0", port=5000, debug=True)

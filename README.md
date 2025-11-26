# XML-agenda webtool

Deze repo bevat een kleine Flask-webapp die hetzelfde doet als je Colab-notebook:
een XML-agenda uploaden en omzetten naar een tekst-export.

## Lokale installatie

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open daarna `http://localhost:5000` in je browser.

## Deploy op Render.com

1. Push deze map naar een nieuwe GitHub-repository.
2. Ga naar Render.com en kies **New + → Web Service**.
3. Koppel je GitHub-repo en kies de main-branch.
4. Render herkent `render.yaml` automatisch. Controleer:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Deploy de service. Na het bouwen krijg je een publieke URL.


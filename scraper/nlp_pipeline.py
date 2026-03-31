import json
import time

import anthropic
from google.cloud import bigquery, secretmanager

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "onepiece-pipeline"
DIALOGUES_TABLE = "onepiece-pipeline.onepiece.dialogues"
SPEAKERS_TABLE = "onepiece-pipeline.onepiece.speakers"
SECRET_NAME = (
    "projects/onepiece-pipeline/secrets/anthropic-api-key/versions/latest"
)
TARGET_PHRASE = "roi des pirates"


# ============================================================
# ÉTAPE 0 — Récupérer la clé API depuis Secret Manager
# ============================================================

def get_anthropic_api_key():
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=SECRET_NAME)
    return response.payload.data.decode("utf-8")


# ============================================================
# ÉTAPE 1 — Créer la table speakers si elle n'existe pas
# ============================================================

def create_speakers_table_if_not_exists(client):
    schema = [
        bigquery.SchemaField("chapter_number", "INTEGER"),
        bigquery.SchemaField("page_number", "INTEGER"),
        bigquery.SchemaField("speaker", "STRING"),
        bigquery.SchemaField("phrase", "STRING"),
        bigquery.SchemaField("luffy_says_it", "BOOLEAN"),
        bigquery.SchemaField("about_luffy", "BOOLEAN"),
    ]
    table = bigquery.Table(SPEAKERS_TABLE, schema=schema)
    client.create_table(table, exists_ok=True)
    print("✅ Table speakers prête")


# ============================================================
# ÉTAPE 2 — Récupérer les pages déjà traitées
# ============================================================

def get_processed_pages(client):
    try:
        query = f"""
            SELECT DISTINCT chapter_number, page_number
            FROM `{SPEAKERS_TABLE}`
        """
        result = client.query(query).result()
        return {(row.chapter_number, row.page_number) for row in result}
    except Exception:
        return set()


# ============================================================
# ÉTAPE 3 — Récupérer les pages avec "roi des pirates"
# ============================================================

def get_relevant_pages(client):
    query = f"""
        SELECT chapter_number, page_number, extracted_text
        FROM `{DIALOGUES_TABLE}`
        WHERE LOWER(extracted_text) LIKE '%{TARGET_PHRASE}%'
        ORDER BY chapter_number, page_number
    """
    result = client.query(query).result()
    return [
        (row.chapter_number, row.page_number, row.extracted_text)
        for row in result
    ]


# ============================================================
# ÉTAPE 4 — Analyser une page avec Claude Haiku
# ============================================================

def analyze_page_with_claude(anthropic_client, text, chapter, page):
    prompt = f"""Voici le texte extrait d'une page de manga One Piece
(chapitre {chapter}, page {page}).

TEXTE:
{text}

Analyse ce texte et trouve toutes les occurrences où
"roi des pirates" est mentionné.

Pour chaque occurrence, réponds UNIQUEMENT en JSON
(sans markdown, sans explication) avec ce format exact:
{{
  "mentions": [
    {{
      "speaker": "nom du personnage qui parle ou narrateur",
      "phrase": "la phrase exacte contenant roi des pirates",
      "luffy_says_it": true ou false,
      "about_luffy": true ou false
    }}
  ]
}}

- luffy_says_it = true si Luffy affirme qu'il sera roi des pirates
- about_luffy = true si quelqu'un d'autre parle de Luffy comme roi

Si aucune mention claire, retourne: {{"mentions": []}}"""

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("=" * 50)
    print("🧠  One Piece — NLP Pipeline (Claude Haiku)")
    print("=" * 50)

    api_key = get_anthropic_api_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    bq_client = bigquery.Client(project=PROJECT_ID)

    create_speakers_table_if_not_exists(bq_client)

    processed = get_processed_pages(bq_client)
    pages = get_relevant_pages(bq_client)

    to_process = [
        (ch, pg, txt) for ch, pg, txt in pages
        if (ch, pg) not in processed
    ]

    print(f"\n📚 {len(to_process)} pages à analyser")

    rows = []
    for chapter_number, page_number, text in to_process:
        print(f"  🧠 Chapitre {chapter_number} page {page_number}...")

        try:
            result = analyze_page_with_claude(
                anthropic_client, text, chapter_number, page_number
            )

            for mention in result.get("mentions", []):
                rows.append({
                    "chapter_number": chapter_number,
                    "page_number": page_number,
                    "speaker": mention.get("speaker", "inconnu"),
                    "phrase": mention.get("phrase", ""),
                    "luffy_says_it": mention.get("luffy_says_it", False),
                    "about_luffy": mention.get("about_luffy", False),
                })

        except Exception as e:
            print(f"  ⚠️ Erreur page {page_number} : {e}")

        time.sleep(0.3)

        if len(rows) >= 50:
            errors = bq_client.insert_rows_json(SPEAKERS_TABLE, rows)
            if errors:
                print(f"  ❌ Erreur BigQuery : {errors}")
            else:
                print(f"  ✅ {len(rows)} lignes chargées")
            rows = []

    if rows:
        errors = bq_client.insert_rows_json(SPEAKERS_TABLE, rows)
        if errors:
            print(f"  ❌ Erreur BigQuery : {errors}")
        else:
            print(f"  ✅ {len(rows)} lignes chargées")

    print("\n🏴‍☠️  NLP Pipeline terminé !")


if __name__ == "__main__":
    main()
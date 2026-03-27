import json

from google.cloud import bigquery

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "onepiece-pipeline"
DATASET_ID = "onepiece"
TABLE_ID = "chapters"

TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


# ============================================================
# ÉTAPE 1 — Lire le fichier output.json
# ============================================================

def load_json(filepath):
    print(f"\n📂 Lecture du fichier {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.get("chapters", [])
    print(f"✅ {len(chapters)} chapitres trouvés dans le fichier")
    return chapters


# ============================================================
# ÉTAPE 2 — Convertir les données au bon format
# ============================================================

def format_chapter(chapter):
    return {
        "id": chapter.get("id"),
        "chapter_number": chapter.get("chapter_number"),
        "title": chapter.get("title"),
        "volume": chapter.get("volume"),
        "language": chapter.get("language"),
        "published_at": chapter.get("published_at"),
        "scraped_at": chapter.get("scraped_at"),
    }


# ============================================================
# ÉTAPE 3 — Envoyer les données dans BigQuery
# ============================================================

def load_to_bigquery(chapters):
    """Envoie la liste de chapitres dans la table BigQuery."""
    print(f"\n☁️  Connexion à BigQuery ({TABLE_REF})...")

    client = bigquery.Client(project=PROJECT_ID)

    # On convertit chaque chapitre au bon format
    rows = [format_chapter(chap) for chap in chapters]

    print(f"📤 Envoi de {len(rows)} chapitres vers BigQuery...")

    # On configure le job de chargement
    # WRITE_TRUNCATE = on écrase les données existantes à chaque fois
    # C'est plus simple pour commencer — on verra WRITE_APPEND plus tard
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    # On lance le chargement
    job = client.load_table_from_json(
        rows,
        TABLE_REF,
        job_config=job_config,
    )

    # On attend que le job soit terminé
    job.result()

    print(f"✅ {len(rows)} chapitres insérés avec succès !")


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    """Orchestre la lecture du JSON et l'envoi vers BigQuery."""
    print("=" * 50)
    print("☁️   One Piece — Chargement vers BigQuery")
    print("=" * 50)

    chapters = load_json("output.json")

    if not chapters:
        print("Aucun chapitre à envoyer.")
        return

    load_to_bigquery(chapters)

    print("\n✅ Chargement terminé !")


if __name__ == "__main__":
    main()

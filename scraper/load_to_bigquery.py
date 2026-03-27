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
    """Lit le fichier JSON produit par le scraper."""
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
    """
    Convertit un chapitre brut en dictionnaire
    compatible avec BigQuery.
    On n'envoie PAS image_urls car c'est une liste —
    BigQuery nécessite un type ARRAY pour ça,
    qu'on ajoutera plus tard.
    """
    return {
        "chapter_number": chapter.get("chapter_number"),
        "url": chapter.get("url"),
        "image_count": chapter.get("image_count", 0),
        "source": "onepiecescan.fr",
        "language": "fr",
        "scraped_at": chapter.get("scraped_at"),
    }


# ============================================================
# ÉTAPE 3 — Envoyer les données dans BigQuery
# ============================================================

def load_to_bigquery(chapters):
    """Envoie la liste de chapitres dans la table BigQuery."""
    print(f"\n☁️  Connexion à BigQuery ({TABLE_REF})...")

    client = bigquery.Client(project=PROJECT_ID)

    rows = [format_chapter(chap) for chap in chapters]

    print(f"📤 Envoi de {len(rows)} chapitres vers BigQuery...")

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    job = client.load_table_from_json(
        rows,
        TABLE_REF,
        job_config=job_config,
    )

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

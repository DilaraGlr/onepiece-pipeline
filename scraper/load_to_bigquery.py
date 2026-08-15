import json
import os
import sys
from datetime import datetime, timezone

from google.cloud import bigquery, storage

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "t-lexicon-231513"
DATASET_ID = "onepiece"
TABLE_ID = "chapters"

TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
STAGING_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}_staging"


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
# ÉTAPE 3a — Créer la staging table si elle n'existe pas
# ============================================================

def create_staging_table_if_not_exists(client):
    """Crée la staging table avec le même schéma que chapters."""
    # Schéma identique à onepiece.chapters (voir terraform/main.tf ligne 54-61)
    schema = [
        bigquery.SchemaField("scraped_at", "TIMESTAMP"),
        bigquery.SchemaField("chapter_number", "INTEGER"),
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("language", "STRING"),
        bigquery.SchemaField("url", "STRING"),
        bigquery.SchemaField("image_count", "INTEGER"),
    ]

    table = bigquery.Table(STAGING_TABLE_REF, schema=schema)
    table = client.create_table(table, exists_ok=True)
    print(f"✅ Staging table {STAGING_TABLE_REF} prête")


# ============================================================
# ÉTAPE 3b — Envoyer les données dans BigQuery
# ============================================================

def load_to_bigquery(chapters):
    """
    Envoie la liste de chapitres dans la table BigQuery via MERGE.

    Utilise une staging table pour éviter les doublons :
    1. Charge les nouvelles données dans chapters_staging (WRITE_TRUNCATE)
    2. MERGE vers chapters : UPDATE si chapter_number existe, INSERT sinon
    3. La staging table est automatiquement vidée au prochain chargement
    """
    print(f"\n☁️  Connexion à BigQuery ({TABLE_REF})...")

    client = bigquery.Client(project=PROJECT_ID)

    # Créer la staging table si elle n'existe pas
    create_staging_table_if_not_exists(client)

    rows = [format_chapter(chap) for chap in chapters]

    print(f"📤 Chargement de {len(rows)} chapitres dans staging table...")

    # Étape 1 : Charger dans la staging table (écrase le contenu précédent)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Vide staging avant
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    job = client.load_table_from_json(
        rows,
        STAGING_TABLE_REF,
        job_config=job_config,
    )

    job.result()
    print(f"✅ Staging table chargée")

    # Étape 2 : MERGE vers la table finale
    print(f"🔀 MERGE vers {TABLE_REF} (dédoublonnage sur chapter_number)...")

    merge_query = f"""
    MERGE `{TABLE_REF}` T
    USING `{STAGING_TABLE_REF}` S
    ON T.chapter_number = S.chapter_number
    WHEN MATCHED THEN
      UPDATE SET
        url = S.url,
        image_count = S.image_count,
        source = S.source,
        language = S.language,
        scraped_at = S.scraped_at
    WHEN NOT MATCHED THEN
      INSERT (chapter_number, url, image_count, source, language, scraped_at)
      VALUES (S.chapter_number, S.url, S.image_count, S.source, S.language, S.scraped_at)
    """

    merge_job = client.query(merge_query)
    merge_job.result()

    # Récupérer le nombre de lignes insérées/mises à jour
    stats = merge_job._properties.get('statistics', {}).get('query', {}).get('dmlStats', {})
    inserted = stats.get('insertedRowCount', 0)
    updated = stats.get('updatedRowCount', 0)

    print(f"✅ MERGE terminé : {inserted} insérés, {updated} mis à jour")
    return len(rows)


# ============================================================
# ÉTAPE 4 — Écrire le statut du job dans GCS
# ============================================================

def write_status_to_gcs(status, records_processed, records_failed, error_message=None):
    """Écrit un fichier status.json dans GCS pour le workflow."""
    bucket_name = "onepiece-manga-images-tlex"
    status_path = "_status/scraper-status.json"

    status_data = {
        "status": status,
        "records_processed": records_processed,
        "records_failed": records_failed,
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(status_path)
        blob.upload_from_string(
            json.dumps(status_data, indent=2),
            content_type="application/json",
        )
        print(f"✅ Statut écrit dans gs://{bucket_name}/{status_path}")
    except Exception as e:
        print(f"⚠️  Impossible d'écrire le statut dans GCS : {e}")


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    """Orchestre la lecture du JSON et l'envoi vers BigQuery."""
    print("=" * 50)
    print("☁️   One Piece — Chargement vers BigQuery")
    print("=" * 50)

    records_processed = 0
    records_failed = 0
    error_message = None

    try:
        if not os.path.exists("output.json"):
            print("ℹ️  Aucun nouveau chapitre à charger (output.json absent)")
            # Pas une erreur : rien à traiter est un cas normal
            write_status_to_gcs("success_empty", 0, 0)
            return

        chapters = load_json("output.json")

        if not chapters:
            print("ℹ️  output.json contient 0 chapitres, rien à charger")
            # Pas une erreur : rien à traiter est un cas normal
            # IMPORTANT : Ne fait AUCUNE requête BigQuery dans ce cas
            write_status_to_gcs("success_empty", 0, 0)
            return

        records_processed = load_to_bigquery(chapters)

        print("\n✅ Chargement terminé !")
        write_status_to_gcs("success", records_processed, records_failed)

    except Exception as e:
        error_message = f"Erreur critique lors du chargement BigQuery : {str(e)}"
        print(f"\n❌ {error_message}")
        write_status_to_gcs("error", records_processed, records_failed, error_message)
        sys.exit(1)


if __name__ == "__main__":
    main()

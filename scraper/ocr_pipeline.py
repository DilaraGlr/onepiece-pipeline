import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery, storage, vision

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "t-lexicon-231513"
TABLE_REF = "t-lexicon-231513.onepiece.chapters"
DIALOGUES_TABLE = "t-lexicon-231513.onepiece.dialogues"
FAILED_PAGES_TABLE = "t-lexicon-231513.onepiece.failed_pages"
BUCKET_NAME = "onepiece-manga-images-tlex"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://onepiecescan.fr",
}


# ============================================================
# ÉTAPE 0 — Créer la table dialogues si elle n'existe pas
# ============================================================

def create_dialogues_table_if_not_exists(client):
    schema = [
        bigquery.SchemaField("chapter_number", "INTEGER"),
        bigquery.SchemaField("page_number", "INTEGER"),
        bigquery.SchemaField("image_url", "STRING"),
        bigquery.SchemaField("gcs_path", "STRING"),
        bigquery.SchemaField("extracted_text", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ]
    table = bigquery.Table(DIALOGUES_TABLE, schema=schema)
    client.create_table(table, exists_ok=True)
    print("✅ Table dialogues prête")


# ============================================================
# ÉTAPE 1 — Récupérer les chapitres déjà traités
# ============================================================

def get_processed_chapters(client):
    """Retourne les numéros de chapitres déjà dans dialogues."""
    try:
        query = f"""
            SELECT DISTINCT chapter_number
            FROM `{DIALOGUES_TABLE}`
        """
        result = client.query(query).result()
        return {row.chapter_number for row in result}
    except Exception:
        return set()


# ============================================================
# ÉTAPE 2 — Récupérer tous les chapitres depuis BigQuery
# ============================================================

def get_all_chapters(client):
    query = f"""
        SELECT chapter_number, url
        FROM `{TABLE_REF}`
        ORDER BY chapter_number
    """
    result = client.query(query).result()
    return [(row.chapter_number, row.url) for row in result]


# ============================================================
# ÉTAPE 3 — Récupérer les URLs des images d'un chapitre
# ============================================================

def get_chapter_images(chapter_url):
    try:
        response = requests.get(
            chapter_url,
            headers=HEADERS,
            timeout=30,
        )
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        images = []
        for img in soup.find_all("img", attrs={"data-src": True}):
            src = img["data-src"]
            if "scans" in src or "jpg" in src or "png" in src:
                images.append(src)
        return images

    except Exception as e:
        print(f"  ⚠️ Erreur scraping : {e}")
        return []


# ============================================================
# ÉTAPE 4 — Télécharger une image et l'uploader dans GCS
# ============================================================

def upload_image_to_gcs(
    storage_client, image_url, chapter_number, page_number
):
    """
    Télécharge une image et l'upload dans GCS.
    Retourne: (gcs_path, error_message)
    - (gcs_path, None) en cas de succès
    - (None, error_message) en cas d'erreur
    """
    try:
        response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=30,
        )
        if response.status_code != 200:
            return (None, f"HTTP {response.status_code} lors du téléchargement")

        ext = "jpg" if "jpg" in image_url.lower() else "png"
        gcs_path = (
            f"chapitre-{chapter_number}/page-{page_number:03d}.{ext}"
        )

        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.upload_from_file(
            io.BytesIO(response.content),
            content_type=f"image/{ext}",
        )
        return (gcs_path, None)

    except Exception as e:
        print(f"  ⚠️ Erreur upload GCS : {e}")
        return (None, f"Erreur GCS upload: {str(e)}")


# ============================================================
# ÉTAPE 5 — Extraire le texte via Cloud Vision OCR
# ============================================================

def extract_text_from_gcs(vision_client, gcs_path):
    gcs_uri = f"gs://{BUCKET_NAME}/{gcs_path}"
    image = vision.Image(
        source=vision.ImageSource(gcs_image_uri=gcs_uri)
    )
    response = vision_client.text_detection(image=image)

    if response.error.message:
        print(f"  ⚠️ Erreur Vision : {response.error.message}")
        return ""

    texts = response.text_annotations
    if texts:
        return texts[0].description.strip()
    return ""


# ============================================================
# ÉCRIRE LE STATUT DU JOB DANS GCS
# ============================================================

def write_status_to_gcs(status, records_processed, records_failed, error_message=None):
    """Écrit un fichier status.json dans GCS pour le workflow."""
    status_data = {
        "status": status,
        "records_processed": records_processed,
        "records_failed": records_failed,
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob("_status/ocr-status.json")
        blob.upload_from_string(
            json.dumps(status_data, indent=2),
            content_type="application/json",
        )
        print(f"✅ Statut écrit dans gs://{BUCKET_NAME}/_status/ocr-status.json")
    except Exception as e:
        print(f"⚠️  Impossible d'écrire le statut dans GCS : {e}")


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("=" * 50)
    print("🔍  One Piece — OCR Pipeline")
    print("=" * 50)

    records_processed = 0
    records_failed = 0
    error_message = None
    failed_pages_records = []  # Dead-letter table pour erreurs item-level

    try:
        limit = int(os.getenv("CHAPTER_LIMIT", "0"))

        bq_client = bigquery.Client(project=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID)
        vision_client = vision.ImageAnnotatorClient()

        create_dialogues_table_if_not_exists(bq_client)

        processed = get_processed_chapters(bq_client)
        all_chapters = get_all_chapters(bq_client)

        to_process = [
            (num, url) for num, url in all_chapters
            if num not in processed
        ]

        if limit > 0:
            to_process = to_process[:limit]
            print(f"\n⚙️  Mode test : {limit} chapitres seulement")

        if not to_process:
            print("\n📚 Aucun nouveau chapitre à traiter")
            write_status_to_gcs("success_empty", 0, 0)
            return

        print(f"\n📚 {len(to_process)} chapitres à traiter")

        for chapter_number, chapter_url in to_process:
            print(f"\n📖 Chapitre {chapter_number}...")

            images = get_chapter_images(chapter_url)
            if not images:
                print("  ⚠️ Aucune image trouvée, on passe")
                # Enregistrer l'erreur chapter-level (page_number = None)
                failed_pages_records.append({
                    "chapter_number": chapter_number,
                    "page_number": None,
                    "pipeline_step": "ocr",
                    "error_type": "no_images_found",
                    "error_message": "Aucune image trouvée pour ce chapitre",
                    "source_url": chapter_url,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                })
                continue

            rows = []
            for page_number, image_url in enumerate(images, start=1):
                print(f"  🖼️  Page {page_number}/{len(images)}...")

                gcs_path, error_msg = upload_image_to_gcs(
                    storage_client,
                    image_url,
                    chapter_number,
                    page_number,
                )
                if not gcs_path:
                    records_failed += 1
                    # Enregistrer l'erreur de téléchargement/upload
                    error_type = "image_download_failed" if "HTTP" in error_msg else "gcs_upload_failed"
                    failed_pages_records.append({
                        "chapter_number": chapter_number,
                        "page_number": page_number,
                        "pipeline_step": "ocr",
                        "error_type": error_type,
                        "error_message": error_msg,
                        "source_url": image_url,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    })
                    continue

                text = extract_text_from_gcs(vision_client, gcs_path)

                rows.append({
                    "chapter_number": chapter_number,
                    "page_number": page_number,
                    "image_url": image_url,
                    "gcs_path": gcs_path,
                    "extracted_text": text,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                })

                time.sleep(0.5)

            if rows:
                errors = bq_client.insert_rows_json(
                    DIALOGUES_TABLE, rows
                )
                if errors:
                    print(f"  ❌ Erreur BigQuery : {errors}")
                    records_failed += len(rows)
                    # Décomposer l'erreur batch en lignes individuelles
                    for row in rows:
                        failed_pages_records.append({
                            "chapter_number": row["chapter_number"],
                            "page_number": row["page_number"],
                            "pipeline_step": "ocr",
                            "error_type": "bigquery_insert_failed",
                            "error_message": str(errors),
                            "source_url": row["gcs_path"],
                            "failed_at": datetime.now(timezone.utc).isoformat(),
                        })
                else:
                    print(f"  ✅ {len(rows)} pages chargées dans BigQuery")
                    records_processed += len(rows)

            time.sleep(1)

        # Insérer toutes les erreurs dans la dead-letter table
        if failed_pages_records:
            print(f"\n📝 Enregistrement de {len(failed_pages_records)} échecs dans failed_pages...")
            bq_errors = bq_client.insert_rows_json(
                FAILED_PAGES_TABLE, failed_pages_records
            )
            if bq_errors:
                print(f"  ⚠️ Erreur lors de l'écriture dans failed_pages : {bq_errors}")
            else:
                print(f"  ✅ {len(failed_pages_records)} échecs enregistrés")

        print(f"\n🏴‍☠️  OCR Pipeline terminé ! ({records_processed} pages traitées, {records_failed} échecs)")
        write_status_to_gcs("success", records_processed, records_failed)

    except Exception as e:
        error_message = f"Erreur critique OCR : {str(e)}"
        print(f"\n❌ {error_message}")
        write_status_to_gcs("error", records_processed, records_failed, error_message)
        sys.exit(1)


if __name__ == "__main__":
    main()
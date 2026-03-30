import io
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery, storage, vision

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "onepiece-pipeline"
TABLE_REF = "onepiece-pipeline.onepiece.chapters"
DIALOGUES_TABLE = "onepiece-pipeline.onepiece.dialogues"
BUCKET_NAME = "onepiece-manga-images"

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
    try:
        response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=30,
        )
        if response.status_code != 200:
            return None

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
        return gcs_path

    except Exception as e:
        print(f"  ⚠️ Erreur upload GCS : {e}")
        return None


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
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("=" * 50)
    print("🔍  One Piece — OCR Pipeline")
    print("=" * 50)

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

    print(f"\n📚 {len(to_process)} chapitres à traiter")

    for chapter_number, chapter_url in to_process:
        print(f"\n📖 Chapitre {chapter_number}...")

        images = get_chapter_images(chapter_url)
        if not images:
            print("  ⚠️ Aucune image trouvée, on passe")
            continue

        rows = []
        for page_number, image_url in enumerate(images, start=1):
            print(f"  🖼️  Page {page_number}/{len(images)}...")

            gcs_path = upload_image_to_gcs(
                storage_client,
                image_url,
                chapter_number,
                page_number,
            )
            if not gcs_path:
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
            else:
                print(f"  ✅ {len(rows)} pages chargées dans BigQuery")

        time.sleep(1)

    print("\n🏴‍☠️  OCR Pipeline terminé !")


if __name__ == "__main__":
    main()
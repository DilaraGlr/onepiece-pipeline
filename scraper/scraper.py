import json
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://onepiecescan.fr"
MANGA_URL = f"{BASE_URL}/manga/one-piece/"
PROJECT_ID = "onepiece-pipeline"
TABLE_REF = "onepiece-pipeline.onepiece.chapters"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}


# ============================================================
# UTILITAIRE — Requête avec retry automatique
# ============================================================

def request_with_retry(url, max_retries=3):
    """
    Appelle une URL avec retry automatique en cas d'erreur.
    Attend 5s, 10s, puis 20s entre chaque tentative.
    C'est ce qu'on appelle un exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30,
            )
            if response.status_code == 200:
                return response

            print(
                f"  ⚠️ Statut {response.status_code} "
                f"pour {url}"
            )

        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ Erreur réseau : {e}")

        if attempt < max_retries - 1:
            wait = 5 * (2 ** attempt)
            print(
                f"  🔄 Tentative {attempt + 1}/{max_retries}"
                f" échouée, retry dans {wait}s..."
            )
            time.sleep(wait)

    print(f"  ❌ Échec après {max_retries} tentatives : {url}")
    return None


# ============================================================
# ÉTAPE 0 — Récupérer le dernier chapitre dans BigQuery
# ============================================================

def get_last_chapter_from_bq():
    """
    Interroge BigQuery pour savoir quel est le dernier
    chapitre déjà stocké. Retourne 0 si la table est vide.
    """
    print("\n🔍 Vérification du dernier chapitre dans BigQuery...")

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT MAX(chapter_number) as last_chapter
        FROM `{TABLE_REF}`
    """
    result = client.query(query).result()
    row = list(result)[0]

    last = row.last_chapter if row.last_chapter else 0
    print(f"✅ Dernier chapitre connu : #{last}")
    return int(last)


# ============================================================
# ÉTAPE 1 — Récupérer la liste de tous les chapitres
# ============================================================

def get_chapter_list():
    """
    Va sur la page principale de One Piece et récupère
    la liste de tous les chapitres disponibles.
    """
    print("\n📚 Récupération de la liste des chapitres...")

    response = request_with_retry(MANGA_URL)

    if not response:
        print("❌ Impossible d'accéder à onepiecescan.fr")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    chapters = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "chapitre" in href.lower() and "vf" in href.lower():
            parts = href.split("chapitre-")
            if len(parts) > 1:
                num = parts[1].split("-vf")[0]
                try:
                    float(num)
                    chapters.append({
                        "number": num,
                        "url": href,
                    })
                except ValueError:
                    pass

    seen = set()
    unique = []
    for chap in chapters:
        if chap["number"] not in seen:
            seen.add(chap["number"])
            unique.append(chap)

    unique.sort(key=lambda x: float(x["number"]))

    print(f"✅ {len(unique)} chapitres trouvés sur le site")
    return unique


# ============================================================
# ÉTAPE 2 — Récupérer les URLs des images d'un chapitre
# ============================================================

def get_chapter_images(chapter_url):
    """
    Va sur la page d'un chapitre et extrait les URLs
    de toutes ses images depuis l'attribut data-src.
    """
    response = request_with_retry(chapter_url)

    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    images = []
    for img in soup.find_all("img", attrs={"data-src": True}):
        src = img["data-src"]
        if "scans" in src or "jpg" in src or "png" in src:
            images.append(src)

    return images


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    """Orchestre le scraping et sauvegarde les résultats."""
    print("=" * 50)
    print("🏴‍☠️  One Piece — Scraper OnePieceScan")
    print("=" * 50)

    limit = int(os.getenv("CHAPTER_LIMIT", "0"))

    if limit > 0:
        last_chapter = 0
        print(f"\n⚙️  Mode test : {limit} premiers chapitres")
    else:
        last_chapter = get_last_chapter_from_bq()

    all_chapters = get_chapter_list()

    if not all_chapters:
        print("Aucun chapitre trouvé.")
        return

    if limit > 0:
        chapters_to_scrape = all_chapters[:limit]
    else:
        chapters_to_scrape = [
            c for c in all_chapters
            if int(float(c["number"])) > last_chapter
        ]

    if not chapters_to_scrape:
        print("\n✅ Aucun nouveau chapitre à scraper !")
        return

    print(
        f"\n🖼️  {len(chapters_to_scrape)} nouveaux chapitres "
        f"à scraper..."
    )

    results = []
    for chap in chapters_to_scrape:
        print(f"  📖 Chapitre {chap['number']}...")
        images = get_chapter_images(chap["url"])

        results.append({
            "chapter_number": chap["number"],
            "url": chap["url"],
            "image_count": len(images),
            "image_urls": images,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })

        print(f"     ✅ {len(images)} images trouvées")
        time.sleep(1)

    output = {
        "manga": "One Piece",
        "source": "onepiecescan.fr",
        "language": "fr",
        "total_chapters_available": len(all_chapters),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "chapters": results,
    }

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n💾 Données sauvegardées dans output.json")
    print(f"✅ Scraping terminé ! ({len(results)} chapitres)")


if __name__ == "__main__":
    main()

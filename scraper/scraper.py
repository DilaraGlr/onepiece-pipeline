import json
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://onepiecescan.fr"
MANGA_URL = f"{BASE_URL}/manga/one-piece/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}


# ============================================================
# ÉTAPE 1 — Récupérer la liste de tous les chapitres
# ============================================================

def get_chapter_list():
    """
    Va sur la page principale de One Piece et récupère
    la liste de tous les chapitres disponibles.
    Retourne une liste de dictionnaires {number, url}.
    """
    print("\n📚 Récupération de la liste des chapitres...")

    response = requests.get(MANGA_URL, headers=HEADERS)

    if response.status_code != 200:
        print(f"Erreur {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # On cherche tous les liens qui contiennent 'chapitre'
    chapters = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "chapitre" in href.lower() and "vf" in href.lower():
            # On extrait le numéro du chapitre depuis l'URL
            # ex: one-piece-scan-chapitre-1-vf → 1
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

    # Dédoublonnage par numéro
    seen = set()
    unique = []
    for chap in chapters:
        if chap["number"] not in seen:
            seen.add(chap["number"])
            unique.append(chap)

    # Tri par numéro
    unique.sort(key=lambda x: float(x["number"]))

    print(f"✅ {len(unique)} chapitres trouvés")
    return unique


# ============================================================
# ÉTAPE 2 — Récupérer les URLs des images d'un chapitre
# ============================================================

def get_chapter_images(chapter_url):
    """
    Va sur la page d'un chapitre et extrait les URLs
    de toutes ses images depuis l'attribut data-src.
    """
    response = requests.get(chapter_url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Erreur {response.status_code} : {chapter_url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Les images sont dans data-src (lazy loading)
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

    # Étape 1 — Liste des chapitres
    chapters = get_chapter_list()

    if not chapters:
        print("Aucun chapitre trouvé.")
        return

    # Étape 2 — Pour chaque chapitre, on récupère les images
    # On commence par les 5 premiers pour tester
    print("\n🖼️  Récupération des images (5 premiers chapitres)...")

    results = []
    for chap in chapters:
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

        # Pause de politesse entre chaque requête
        time.sleep(1)

    # Sauvegarde
    output = {
        "manga": "One Piece",
        "source": "onepiecescan.fr",
        "language": "fr",
        "total_chapters_available": len(chapters),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "chapters": results,
    }

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n💾 Données sauvegardées dans output.json")
    print(f"✅ Scraping terminé ! ({len(results)} chapitres)")


if __name__ == "__main__":
    main()

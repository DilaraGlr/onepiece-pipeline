"""
Génération de Signed URLs pour partager temporairement des images GCS.

Pourquoi utiliser des Signed URLs plutôt que rendre le bucket public ?

1. SÉCURITÉ - Accès temporaire uniquement :
   - L'URL expire après un délai défini (ex: 15 minutes)
   - Pas besoin de laisser le bucket public en permanence
   - Révocable : l'accès expire automatiquement

2. CONTRÔLE D'ACCÈS - Pas de compte GCP requis :
   - Le destinataire n'a pas besoin d'un compte Google Cloud
   - Pas besoin de gérer des permissions IAM pour des utilisateurs externes
   - Partage simple via un lien temporaire

3. AUDIT - Traçabilité :
   - Chaque URL est unique et signée cryptographiquement
   - Impossible de deviner ou forger une URL valide
   - Les logs GCS enregistrent les accès

4. MOINDRE PRIVILÈGE (Chapitre 2) :
   - Accès limité à UN objet spécifique (pas tout le bucket)
   - Durée de vie limitée (pas d'accès permanent)
   - Conforme au principe du moindre privilège

Exemple d'utilisation :
    python generate_signed_url.py chapitre-1/page-001.jpg
    python generate_signed_url.py chapitre-1/page-001.jpg 60  # expire après 60 min
"""

import sys
from datetime import datetime, timedelta, timezone

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "t-lexicon-231513"
BUCKET_NAME = "onepiece-manga-images-tlex"


# ============================================================
# GÉNÉRATION DE SIGNED URL
# ============================================================

def generate_signed_url(gcs_path: str, expiration_minutes: int = 15) -> str:
    """
    Génère une URL signée v4 pour un objet GCS.

    Args:
        gcs_path: Chemin de l'objet dans le bucket (ex: "chapitre-1/page-001.jpg")
        expiration_minutes: Durée de validité de l'URL en minutes (défaut: 15)

    Returns:
        str: URL signée temporaire permettant l'accès sans authentification

    Raises:
        google.cloud.exceptions.NotFound: Si l'objet n'existe pas dans le bucket
        google.auth.exceptions.DefaultCredentialsError: Si les credentials sont invalides

    Example:
        >>> url = generate_signed_url("chapitre-1/page-001.jpg", expiration_minutes=30)
        >>> print(url)
        https://storage.googleapis.com/onepiece-manga-images-tlex/chapitre-1/page-001.jpg?X-Goog-Algorithm=...
    """
    # Service account utilisé pour signer l'URL
    service_account_email = "sa-job-data@t-lexicon-231513.iam.gserviceaccount.com"

    # Obtenir les credentials par défaut
    source_credentials, _ = google.auth.default()

    # Créer credentials impersonalisées pour signer
    # L'utilisateur doit avoir iam.serviceAccounts.signBlob sur ce SA
    target_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=service_account_email,
        target_scopes=target_scopes,
    )

    # Initialiser le client Storage avec les credentials impersonalisées
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)

    # Vérifier que l'objet existe
    if not blob.exists():
        raise FileNotFoundError(
            f"L'objet '{gcs_path}' n'existe pas dans le bucket '{BUCKET_NAME}'"
        )

    # Générer l'URL signée v4 avec signature IAM côté serveur
    # Version 4 : signature plus sécurisée que v2, supporte des durées plus longues
    # service_account_email : utilise IAM pour signer (pas besoin de clé privée locale)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",  # Autoriser uniquement la lecture (pas PUT/DELETE)
        service_account_email=service_account_email,
    )

    return url


# ============================================================
# CLI - UTILISATION EN LIGNE DE COMMANDE
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_signed_url.py <gcs_path> [expiration_minutes]")
        print("")
        print("Arguments:")
        print("  gcs_path             Chemin de l'objet dans le bucket (ex: chapitre-1/page-001.jpg)")
        print("  expiration_minutes   Durée de validité en minutes (défaut: 15)")
        print("")
        print("Exemples:")
        print("  python generate_signed_url.py chapitre-1/page-001.jpg")
        print("  python generate_signed_url.py chapitre-1/page-001.jpg 60")
        sys.exit(1)

    # Récupérer les arguments
    gcs_path = sys.argv[1]
    expiration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    try:
        # Générer l'URL signée
        print(f"🔗 Génération d'une Signed URL pour : {gcs_path}")
        print(f"⏱️  Expiration : {expiration_minutes} minutes")
        print("")

        url = generate_signed_url(gcs_path, expiration_minutes)

        # Calculer l'heure d'expiration
        expiration_time = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)

        # Afficher les résultats
        print("✅ URL signée générée avec succès :")
        print("")
        print(url)
        print("")
        print(f"📅 Expire le : {expiration_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"⏰ Temps restant : {expiration_minutes} minutes")
        print("")
        print("💡 Cette URL permet de télécharger l'image sans compte GCP.")
        print("💡 Elle expirera automatiquement après la durée spécifiée.")

    except FileNotFoundError as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors de la génération de l'URL : {e}")
        sys.exit(1)

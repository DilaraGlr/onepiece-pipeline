set -e

# Configuration
PROJECT_ID="onepiece-pipeline"
REGION="europe-west1"
REPOSITORY="onepiece-repo"
IMAGE_NAME="scraper"
TAG="latest"

# Construire l'URL complète de l'image
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

echo "=================================================="
echo "Build et push de l'image Scraper/OCR"
echo "=================================================="
echo "Image: ${IMAGE_URL}"
echo ""

# Se déplacer dans le répertoire scraper
cd scraper

# Construire l'image Docker pour linux/amd64 (requis par Cloud Run)
echo "📦 Construction de l'image Docker (linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile -t ${IMAGE_URL} .

echo ""
echo "🔐 Authentification à Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo ""
echo "⬆️  Push de l'image vers Artifact Registry..."
docker push ${IMAGE_URL}

echo ""
echo "✅ Image Scraper/OCR pushée avec succès!"
echo "   ${IMAGE_URL}"
echo ""
echo "Cette image est utilisée par:"
echo "   - onepiece-scraper-job (PIPELINE_MODE=scraper)"
echo "   - ocr-pipeline-job (PIPELINE_MODE=ocr)"

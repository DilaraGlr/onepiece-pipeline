#!/bin/bash

# Script pour construire et pusher l'image Docker du NLP pipeline vers Artifact Registry

set -e

# Configuration
PROJECT_ID="onepiece-pipeline"
REGION="europe-west1"
REPOSITORY="onepiece-repo"
IMAGE_NAME="nlp-pipeline"
TAG="latest"

# Construire l'URL complète de l'image
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

echo "=================================================="
echo "Build et push de l'image NLP Pipeline"
echo "=================================================="
echo "Image: ${IMAGE_URL}"
echo ""

# Se déplacer dans le répertoire scraper
cd scraper

# Construire l'image Docker pour linux/amd64 (requis par Cloud Run)
echo "📦 Construction de l'image Docker (linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile.nlp -t ${IMAGE_URL} .

echo ""
echo "🔐 Authentification à Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo ""
echo "⬆️  Push de l'image vers Artifact Registry..."
docker push ${IMAGE_URL}

echo ""
echo "✅ Image NLP Pipeline pushée avec succès!"
echo "   ${IMAGE_URL}"
echo ""
echo "Pour déployer sur Cloud Run, exécutez:"
echo "   cd terraform"
echo "   terraform apply"

#!/bin/bash

# Script de déploiement complet du pipeline One Piece
# Déploie l'infrastructure from scratch dans le bon ordre

set -e  # Arrêter en cas d'erreur

# Configuration
PROJECT_ID="onepiece-pipeline"
REGION="europe-west1"
REPOSITORY="onepiece-repo"

echo "============================================================"
echo "🏴‍☠️  DÉPLOIEMENT COMPLET DU PIPELINE ONE PIECE"
echo "============================================================"
echo ""
echo "Projet: ${PROJECT_ID}"
echo "Région: ${REGION}"
echo ""

# ============================================================
# ÉTAPE 1 : BUILD ET PUSH DES IMAGES DOCKER
# ============================================================

echo "============================================================"
echo "📦 ÉTAPE 1/3 : Build et push des images Docker"
echo "============================================================"
echo ""

cd scraper

echo "▶️  1/3 - Build de l'image Scraper/OCR..."
docker build --platform linux/amd64 -f Dockerfile -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/scraper:latest .
echo "✅ Image Scraper/OCR buildée"
echo ""

echo "▶️  2/3 - Build de l'image Dashboard..."
docker build --platform linux/amd64 -f Dockerfile.dashboard -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/dashboard:latest .
echo "✅ Image Dashboard buildée"
echo ""

echo "▶️  3/3 - Build de l'image NLP..."
docker build --platform linux/amd64 -f Dockerfile.nlp -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/nlp-pipeline:latest .
echo "✅ Image NLP buildée"
echo ""

echo "🔐 Authentification à Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
echo ""

echo "⬆️  Push des 3 images vers Artifact Registry..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/scraper:latest
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/dashboard:latest
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/nlp-pipeline:latest
echo ""
echo "✅ Toutes les images sont pushées!"
echo ""

cd ..

# ============================================================
# ÉTAPE 2 : DÉPLOIEMENT TERRAFORM
# ============================================================

echo "============================================================"
echo "🏗️  ÉTAPE 2/3 : Déploiement de l'infrastructure Terraform"
echo "============================================================"
echo ""

cd terraform

echo "▶️  Initialisation de Terraform..."
terraform init
echo ""

echo "▶️  Déploiement de l'infrastructure..."
terraform apply -auto-approve
echo ""
echo "✅ Infrastructure déployée!"
echo ""

cd ..

# ============================================================
# ÉTAPE 3 : DÉPLOIEMENT DU WORKFLOW
# ============================================================

echo "============================================================"
echo "🔄 ÉTAPE 3/3 : Déploiement du Cloud Workflow"
echo "============================================================"
echo ""

echo "▶️  Déploiement du workflow onepiece-workflow..."
gcloud workflows deploy onepiece-workflow \
  --location=${REGION} \
  --source=scraper/workflow.yaml \
  --project=${PROJECT_ID}
echo ""
echo "✅ Workflow déployé!"
echo ""

# ============================================================
# RÉSUMÉ FINAL
# ============================================================

echo "============================================================"
echo "🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS!"
echo "============================================================"
echo ""
echo "✅ 3 images Docker pushées vers Artifact Registry"
echo "✅ Infrastructure Terraform déployée"
echo "✅ Cloud Workflow déployé"
echo ""
echo "📊 Ressources déployées:"
echo "   - Cloud Run Jobs: scraper, ocr, nlp"
echo "   - Cloud Run Service: dashboard"
echo "   - Cloud Workflows: onepiece-workflow"
echo "   - Cloud Scheduler: onepiece-scheduler (lundi 9h)"
echo "   - BigQuery: dataset onepiece + 3 tables"
echo "   - Cloud Storage: bucket manga-images"
echo ""
echo "🌐 Dashboard URL:"
cd terraform
terraform output dashboard_url
cd ..
echo ""
echo "🚀 Pour lancer le pipeline manuellement:"
echo "   gcloud workflows run onepiece-workflow --location=${REGION}"
echo ""
echo "============================================================"

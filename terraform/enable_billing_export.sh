#!/bin/bash
# ============================================================
# SCRIPT D'ACTIVATION DE L'EXPORT DE FACTURATION BIGQUERY
# ============================================================
#
# Ce script configure automatiquement l'export de facturation
# vers le dataset BigQuery créé par Terraform.
#
# PRÉREQUIS :
# - gcloud CLI installé et authentifié
# - Permissions billing.accounts.update sur le compte de facturation
# - Le dataset BigQuery billing_export doit exister (créé par Terraform)
#
# UTILISATION :
#   chmod +x enable_billing_export.sh
#   ./enable_billing_export.sh
# ============================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Configuration de l'export de facturation BigQuery${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

# Charger les variables depuis terraform.tfvars
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}Erreur : terraform.tfvars non trouvé${NC}"
    echo -e "${YELLOW}Copiez terraform.tfvars.example vers terraform.tfvars et remplissez vos valeurs${NC}"
    exit 1
fi

# Extraire les valeurs (simple parsing - fonctionne pour le format basique)
PROJECT_ID=$(grep "^project_id" terraform.tfvars | cut -d'"' -f2)
BILLING_ACCOUNT_ID=$(grep "^billing_account_id" terraform.tfvars | cut -d'"' -f2)

if [ -z "$PROJECT_ID" ] || [ -z "$BILLING_ACCOUNT_ID" ] || [ "$BILLING_ACCOUNT_ID" == "XXXXXX-XXXXXX-XXXXXX" ]; then
    echo -e "${RED}Erreur : Variables manquantes dans terraform.tfvars${NC}"
    echo -e "${YELLOW}Vérifiez que project_id et billing_account_id sont correctement configurés${NC}"
    exit 1
fi

DATASET_ID="billing_export"
DATASET_LOCATION="US"

echo -e "Configuration détectée :"
echo -e "  ${YELLOW}Projet :${NC} $PROJECT_ID"
echo -e "  ${YELLOW}Compte de facturation :${NC} $BILLING_ACCOUNT_ID"
echo -e "  ${YELLOW}Dataset BigQuery :${NC} $DATASET_ID"
echo -e "  ${YELLOW}Localisation :${NC} $DATASET_LOCATION"
echo ""

# Vérifier que le dataset existe
echo -e "${YELLOW}Vérification du dataset BigQuery...${NC}"
if ! bq ls --project_id="$PROJECT_ID" "$DATASET_ID" &>/dev/null; then
    echo -e "${RED}Erreur : Le dataset $DATASET_ID n'existe pas${NC}"
    echo -e "${YELLOW}Exécutez d'abord : terraform apply${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dataset BigQuery trouvé${NC}"
echo ""

# Note : L'activation de l'export de facturation ne peut pas être faite
# directement via gcloud CLI de manière simple. Elle nécessite :
# 1. L'API Cloud Billing (REST API)
# 2. Ou la console GCP

echo -e "${YELLOW}============================================================${NC}"
echo -e "${YELLOW}ACTIVATION MANUELLE REQUISE${NC}"
echo -e "${YELLOW}============================================================${NC}"
echo ""
echo -e "L'export de facturation doit être activé manuellement via la console GCP."
echo ""
echo -e "${GREEN}Étapes à suivre :${NC}"
echo ""
echo -e "1. Ouvrez : ${YELLOW}https://console.cloud.google.com/billing/${BILLING_ACCOUNT_ID}${NC}"
echo ""
echo -e "2. Dans le menu de gauche, cliquez sur ${YELLOW}\"Billing export\"${NC}"
echo ""
echo -e "3. Sous ${YELLOW}\"BigQuery export\"${NC}, cliquez sur ${YELLOW}\"EDIT SETTINGS\"${NC}"
echo ""
echo -e "4. Pour ${YELLOW}\"Detailed usage cost\"${NC} (recommandé) :"
echo -e "   - Cochez la case pour activer"
echo -e "   - Sélectionnez le projet : ${YELLOW}$PROJECT_ID${NC}"
echo -e "   - Sélectionnez le dataset : ${YELLOW}$DATASET_ID${NC}"
echo -e "   - Cliquez ${YELLOW}\"Save\"${NC}"
echo ""
echo -e "5. (Optionnel) Pour ${YELLOW}\"Pricing export\"${NC} :"
echo -e "   - Répétez les mêmes étapes"
echo ""
echo -e "${GREEN}Vérification après activation :${NC}"
echo ""
echo -e "Après ~24h, vérifiez que les données arrivent avec cette requête :"
echo ""
echo -e "${YELLOW}bq query --project_id=$PROJECT_ID --use_legacy_sql=false '${NC}"
echo -e "SELECT"
echo -e "  service.description AS service,"
echo -e "  SUM(cost) AS total_cost,"
echo -e "  currency"
echo -e "FROM \\\`$PROJECT_ID.$DATASET_ID.gcp_billing_export_v1_*\\\`"
echo -e "WHERE DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)"
echo -e "GROUP BY service, currency"
echo -e "ORDER BY total_cost DESC"
echo -e "LIMIT 10${YELLOW}'${NC}"
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Configuration terminée !${NC}"
echo -e "${GREEN}============================================================${NC}"

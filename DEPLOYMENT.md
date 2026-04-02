# Migration du Dashboard vers Cloud Run

Ce guide explique comment déployer le dashboard One Piece sur Google Cloud Run.

## Changements effectués

### 1. Dockerfile.dashboard
Création d'un nouveau Dockerfile spécifique pour le dashboard:
- Port 8080 (requis par Cloud Run)
- Image optimisée avec Streamlit

### 2. dashboard.py
Modification pour supporter les deux environnements:
- **Cloud Run**: Utilise les Application Default Credentials (automatique)
- **Local/Streamlit Cloud**: Utilise `st.secrets` (secrets.toml)

### 3. Terraform
Ajout de la ressource Cloud Run Service:
- Service public (noauth)
- Scaling automatique (0-10 instances)
- 512Mi de RAM, 1 CPU
- URL publique disponible en output

### 4. Script de build
Script `build-and-push-dashboard.sh` pour construire et pusher l'image Docker.

## Instructions de déploiement

### Étape 1: Construire et pusher l'image Docker

```bash
./build-and-push-dashboard.sh
```

Ce script va:
1. Construire l'image Docker du dashboard
2. L'authentifier à Artifact Registry
3. Pusher l'image vers `europe-west1-docker.pkg.dev/onepiece-pipeline/onepiece-repo/dashboard:latest`

### Étape 2: Déployer avec Terraform

```bash
cd terraform
terraform plan
terraform apply
```

Terraform va créer:
- Un service Cloud Run pour le dashboard
- Un IAM binding pour l'accès public
- Une URL publique (affichée dans les outputs)

### Étape 3: Récupérer l'URL du dashboard

```bash
cd terraform
terraform output dashboard_url
```

Ou via la console GCP:
https://console.cloud.google.com/run?project=onepiece-pipeline

### Étape 4: Supprimer le déploiement Streamlit Cloud

Une fois que le dashboard Cloud Run fonctionne correctement:
1. Allez sur https://share.streamlit.io/
2. Supprimez l'app existante

## Permissions

Le service Cloud Run utilise automatiquement le service account par défaut de Compute Engine qui a déjà accès à BigQuery.

Si vous rencontrez des problèmes de permissions, vérifiez que le service account `682150386282-compute@developer.gserviceaccount.com` a les rôles:
- `roles/bigquery.dataViewer`
- `roles/bigquery.jobUser`

## Variables d'environnement

Cloud Run détecte automatiquement qu'il est sur Cloud Run via la variable `K_SERVICE`.
Aucune configuration supplémentaire n'est nécessaire.

## Rollback

Si vous devez revenir en arrière:

1. Supprimer le service Cloud Run:
```bash
cd terraform
terraform destroy -target=google_cloud_run_v2_service.dashboard
terraform destroy -target=google_cloud_run_service_iam_member.dashboard_public
```

2. Restaurer l'ancien code dashboard.py depuis git:
```bash
git checkout HEAD~1 -- scraper/dashboard.py
```

## Coûts

Cloud Run avec scaling à 0 est gratuit quand il n'y a pas de trafic.
Avec du trafic léger, le coût devrait être très faible (quelques centimes par mois).

## Support local

Le dashboard fonctionne toujours en local avec:
```bash
cd scraper
streamlit run dashboard.py
```

Il utilisera automatiquement `secrets.toml` si la variable `K_SERVICE` n'est pas définie.

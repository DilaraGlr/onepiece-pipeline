# Commandes pour la présentation One Piece Pipeline

## 1. Montrer l'infrastructure Terraform

```bash
cd terraform
terraform show
```

Ou pour un aperçu plus concis:

```bash
cd terraform
terraform state list
```

## 2. Lancer le pipeline complet

```bash
gcloud workflows run onepiece-workflow --location=europe-west1
```

Suivre l'exécution du workflow:

```bash
gcloud workflows executions list onepiece-workflow --location=europe-west1 --limit=1
```

Voir les logs du workflow:

```bash
gcloud workflows executions describe <EXECUTION_ID> --location=europe-west1 --workflow=onepiece-workflow
```

## 3. Vérifier les données dans BigQuery

### Nombre de chapitres scrapés

```bash
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.chapters`'
```

### Nombre de pages OCR traitées

```bash
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.dialogues`'
```

### Nombre de mentions "Roi des Pirates"

```bash
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.speakers`'
```

### Voir des exemples de données

```bash
bq query --use_legacy_sql=false 'SELECT * FROM `onepiece-pipeline.onepiece.chapters` ORDER BY chapter_number DESC LIMIT 10'
```

```bash
bq query --use_legacy_sql=false 'SELECT chapter_number, speaker, phrase FROM `onepiece-pipeline.onepiece.speakers` WHERE luffy_says_it = true LIMIT 10'
```

## 4. Dashboard Streamlit sur Cloud Run

Ouvrir le dashboard dans le navigateur:

```
https://onepiece-dashboard-682150386282.europe-west1.run.app
```

Ou récupérer l'URL via Terraform:

```bash
cd terraform
terraform output dashboard_url
```

## 5. Montrer les jobs Cloud Run

### Lister tous les jobs

```bash
gcloud run jobs list --region=europe-west1
```

### Voir les détails d'un job

```bash
gcloud run jobs describe onepiece-scraper-job --region=europe-west1
gcloud run jobs describe ocr-pipeline-job --region=europe-west1
gcloud run jobs describe nlp-pipeline-job --region=europe-west1
```

### Voir le service dashboard

```bash
gcloud run services describe onepiece-dashboard --region=europe-west1
```

### Lancer manuellement un job

```bash
# Scraper
gcloud run jobs execute onepiece-scraper-job --region=europe-west1

# OCR
gcloud run jobs execute ocr-pipeline-job --region=europe-west1

# NLP
gcloud run jobs execute nlp-pipeline-job --region=europe-west1
```

## 6. Montrer le Scheduler

### Lister les jobs planifiés

```bash
gcloud scheduler jobs list --location=europe-west1
```

### Voir les détails du scheduler

```bash
gcloud scheduler jobs describe onepiece-scheduler --location=europe-west1
```

### Déclencher manuellement le scheduler

```bash
gcloud scheduler jobs run onepiece-scheduler --location=europe-west1
```

## 7. Voir les logs

### Logs du workflow

```bash
gcloud logging read "resource.type=workflows.googleapis.com/Workflow" --limit=50 --format=json
```

### Logs du scraper

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=onepiece-scraper-job" --limit=50
```

### Logs de l'OCR

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=ocr-pipeline-job" --limit=50
```

### Logs du NLP

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=nlp-pipeline-job" --limit=50
```

### Logs du dashboard

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=onepiece-dashboard" --limit=50
```

## 8. Statistiques et métriques

### Coûts estimés

```bash
gcloud billing accounts list
```

### Vérifier les images dans Artifact Registry

```bash
gcloud artifacts docker images list europe-west1-docker.pkg.dev/onepiece-pipeline/onepiece-repo
```

### Vérifier les données dans Cloud Storage

```bash
gsutil ls -lh gs://onepiece-manga-images/ | head -20
```

## 9. Architecture complète

```bash
# Ressources BigQuery
bq ls onepiece-pipeline:onepiece

# Buckets GCS
gsutil ls

# Secrets
gcloud secrets list

# Cloud Run (jobs + services)
gcloud run jobs list --region=europe-west1
gcloud run services list --region=europe-west1

# Workflows
gcloud workflows list --location=europe-west1

# Schedulers
gcloud scheduler jobs list --location=europe-west1
```

## 10. Démonstration du pipeline end-to-end

### Étape 1: Lancer le workflow

```bash
gcloud workflows run onepiece-workflow --location=europe-west1
```

### Étape 2: Suivre l'exécution (dans un autre terminal)

```bash
watch -n 5 'gcloud run jobs executions list --region=europe-west1 --limit=3'
```

### Étape 3: Vérifier les résultats

```bash
# Attendre que le workflow se termine
sleep 60

# Vérifier les nouvelles données
bq query --use_legacy_sql=false 'SELECT MAX(chapter_number) as dernier_chapitre FROM `onepiece-pipeline.onepiece.chapters`'
```

### Étape 4: Ouvrir le dashboard

Ouvrir https://onepiece-dashboard-682150386282.europe-west1.run.app dans le navigateur

## Notes pour la présentation

- **Workflow**: Orchestre automatiquement Scraper → OCR → NLP
- **Scheduler**: Déclenche le workflow tous les lundis à 9h
- **Scaling**: Cloud Run scale automatiquement de 0 à N instances
- **Coûts**: Pay-per-use, gratuit quand rien ne tourne
- **Infrastructure as Code**: Tout est défini dans Terraform
- **Dashboard**: Déployé sur Cloud Run, accessible publiquement

---

## Commandes essentielles (dans l'ordre)

### 1. Montrer l'infrastructure Terraform
```bash
cd terraform
terraform show
```

### 2. Lancer le pipeline complet
```bash
gcloud workflows run onepiece-workflow --location=europe-west1
```

### 3. Vérifier que les données sont en BigQuery
```bash
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.chapters`'
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.dialogues`'
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `onepiece-pipeline.onepiece.speakers`'
```

### 4. Ouvrir le dashboard
```
https://onepiece-dashboard-682150386282.europe-west1.run.app
```

### 5. Montrer les jobs Cloud Run
```bash
gcloud run jobs list --region=europe-west1
```

### 6. Montrer le Scheduler
```bash
gcloud scheduler jobs list --location=europe-west1
```

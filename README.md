# 🏴‍☠️ One Piece Data Pipeline

A fully automated end-to-end data pipeline on **Google Cloud Platform** — scraping One Piece chapters, extracting dialogue via OCR, running NLP analysis, and serving a statistics dashboard updated every week.

---

## ⚙️ Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Cloud Run Job      │────▶│  Cloud Run Job   │────▶│  Cloud Run Job  │
│  scraper            │     │  ocr-pipeline    │     │  nlp-pipeline   │
│  (page scraping)    │     │  (text           │     │  (NLP dialogue  │
│                     │     │   extraction)    │     │   analysis)     │
└─────────────────────┘     └──────────────────┘     └────────┬────────┘
         │                                                     │
         ▼                                                     ▼
┌─────────────────────┐                            ┌──────────────────┐
│  Cloud Storage      │                            │  BigQuery        │
│  manga-images       │                            │  dataset onepiece│
│  (raw page images)  │                            │  (3 tables)      │
└─────────────────────┘                            └────────┬─────────┘
                                                            │
                                                   ┌────────▼─────────┐
                                                   │  Cloud Run       │
                                                   │  dashboard       │
                                                   │  (visualisation) │
                                                   └──────────────────┘

            Orchestration: Cloud Workflows ──── Cloud Scheduler (Monday 9am)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Scraping & OCR | Python · Docker (`PIPELINE_MODE=scraper/ocr`) |
| NLP Analysis | Python · Docker (`nlp-pipeline`) |
| Dashboard | Python · Cloud Run Service |
| Orchestration | GCP Cloud Workflows (`workflow.yaml`) |
| Scheduling | GCP Cloud Scheduler (every Monday at 9am) |
| Image storage | GCP Cloud Storage (`manga-images`) |
| Data storage | GCP BigQuery (dataset `onepiece`, 3 tables) |
| Image registry | GCP Artifact Registry (`onepiece-repo`) |
| Infrastructure | Terraform (HCL) |
| CI/CD | Shell scripts (`build-and-push-*.sh`) |

---

## 📁 Project Structure

```
onepiece-pipeline/
├── scraper/
│   ├── Dockerfile              # Scraper + OCR image (PIPELINE_MODE)
│   ├── Dockerfile.dashboard    # Dashboard image
│   ├── Dockerfile.nlp          # NLP image
│   └── workflow.yaml           # Cloud Workflow definition
├── terraform/                  # Infrastructure as Code (GCP)
├── build-and-push-scraper.sh   # Build & push scraper/OCR image
├── build-and-push-dashboard.sh # Build & push dashboard image
├── build-and-push-nlp.sh       # Build & push NLP image
└── deploy.sh                   # 🚀 Full from-scratch deployment
```

---

## 🚀 Deployment

### Prerequisites

- [Docker](https://www.docker.com/)
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk)
- [Terraform](https://www.terraform.io/)
- An active GCP project with the required APIs enabled

### Full deployment (from scratch)

```bash
git clone https://github.com/DilaraGlr/onepiece-pipeline.git
cd onepiece-pipeline

./deploy.sh
```

The script automatically runs 3 steps:

1. **Build & push** the 3 Docker images to Artifact Registry
2. **Terraform deployment** of the full GCP infrastructure
3. **Cloud Workflow deployment**

### Run the pipeline manually

```bash
gcloud workflows run onepiece-workflow --location=europe-west1
```

### Update a single image

```bash
./build-and-push-scraper.sh    # Scraper + OCR
./build-and-push-dashboard.sh  # Dashboard
./build-and-push-nlp.sh        # NLP
```

---

## ☁️ Deployed GCP Resources

| Resource | Name |
|---|---|
| Cloud Run Jobs | `onepiece-scraper-job`, `ocr-pipeline-job`, `nlp` |
| Cloud Run Service | `dashboard` |
| Cloud Workflow | `onepiece-workflow` |
| Cloud Scheduler | `onepiece-scheduler` — every Monday at 9am |
| BigQuery | dataset `onepiece` + 3 tables |
| Cloud Storage | bucket `manga-images` |
| Artifact Registry | `onepiece-repo` |

---

## 📊 What the pipeline produces

- Full dialogue extraction from every One Piece chapter
- Character identification and line count
- Statistics: who speaks the most, per arc, per chapter
- Dashboard automatically refreshed every week with the latest chapter

---

## ⚙️ Configuration

| Variable | Description |
|---|---|
| `PROJECT_ID` | `onepiece-pipeline` |
| `REGION` | `europe-west1` |
| `REPOSITORY` | `onepiece-repo` |
| `PIPELINE_MODE` | `scraper` or `ocr` (shared Docker image) |

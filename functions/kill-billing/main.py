"""
Cloud Function : Budget Killer - Protection Anti-Dérapage

⚠️  ACTION DESTRUCTIVE ⚠️

Cette fonction détache automatiquement le compte de facturation du projet
lorsque le budget atteint 100%, arrêtant TOUTES les ressources Cloud :
- Cloud Run (dashboard, jobs)
- Cloud Scheduler
- BigQuery
- Cloud Storage
- Et TOUT le reste

C'est volontaire : c'est la SEULE vraie barrière contre les dérapages budgétaires.
Un budget seul ne fait que NOTIFIER, il ne coupe jamais la dépense.

Principe de sécurité (Chapitre 2 - Moindre privilège) :
Le service account qui exécute cette fonction a UNIQUEMENT le rôle
roles/billing.projectManager, juste assez pour détacher la facturation,
rien de plus (pas d'Owner, pas d'Editor).

Comportement :
- Ratio < 100% : Logue et ne fait rien
- Ratio >= 100% : Détache la facturation (billingAccountName = "")

Une fois la facturation détachée, le projet devient inutilisable jusqu'à
ce que vous la rattachiez manuellement via la console GCP.
"""

import base64
import json
import os
from typing import Any

from googleapiclient import discovery


def stop_billing(cloud_event: Any, context: Any = None) -> None:
    """
    Fonction déclenchée par Pub/Sub au dépassement du budget.

    Args:
        cloud_event: CloudEvent Pub/Sub contenant le message du budget
        context: Contexte d'exécution (non utilisé en Cloud Functions 2e gen)
    """
    # DEBUG: Logger le CloudEvent brut pour faciliter le debug
    print(f"🔍 DEBUG - CloudEvent reçu (type: {type(cloud_event)})")
    print(f"🔍 DEBUG - CloudEvent content: {cloud_event}")

    # Décoder le message Pub/Sub
    # IMPORTANT: Avec la signature legacy (2 paramètres), le Functions Framework
    # passe directement le dict Pub/Sub au format {"data": "<base64>", "attributes": {...}}
    # sans niveau "message" imbriqué
    pubsub_message = base64.b64decode(cloud_event["data"])

    # DEBUG: Logger le message décodé brut avant parsing JSON
    print(f"🔍 DEBUG - Message décodé: {pubsub_message}")

    budget_notification = json.loads(pubsub_message)

    print(f"📩 Budget notification reçue: {json.dumps(budget_notification, indent=2)}")

    # Extraire les montants
    cost_amount = budget_notification.get("costAmount", 0)
    budget_amount = budget_notification.get("budgetAmount", 0)

    if budget_amount == 0:
        print("⚠️  Budget amount est 0, impossible de calculer le ratio. Abandon.")
        return

    # Calculer le ratio de dépense
    cost_ratio = cost_amount / budget_amount
    print(f"💰 Dépense actuelle: {cost_amount} / Budget: {budget_amount}")
    print(f"📊 Ratio: {cost_ratio:.2%}")

    # N'agir que si le budget est atteint ou dépassé
    if cost_ratio < 1.0:
        print(f"✅ Budget OK ({cost_ratio:.2%}). Aucune action nécessaire.")
        return

    # ⚠️  SEUIL ATTEINT - DÉTACHER LA FACTURATION ⚠️
    print("🚨 ALERTE: Budget atteint à 100% ou plus!")
    print("🔪 Détachement de la facturation du projet...")

    project_id = os.environ.get("GCP_PROJECT")
    if not project_id:
        print("❌ Erreur: GCP_PROJECT non défini dans l'environnement")
        return

    project_name = f"projects/{project_id}"

    try:
        # Appeler l'API Cloud Billing pour détacher le compte
        billing = discovery.build(
            "cloudbilling",
            "v1",
            cache_discovery=False,
        )

        # Détacher = définir billingAccountName à vide
        billing.projects().updateBillingInfo(
            name=project_name,
            body={"billingAccountName": ""},  # Vide = détaché
        ).execute()

        print(f"✅ Facturation détachée avec succès pour {project_name}")
        print("⚠️  TOUTES les ressources Cloud sont maintenant arrêtées")
        print("⚠️  Pour réactiver: GCP Console > Billing > Réattacher le compte")

    except Exception as e:
        print(f"❌ Erreur lors du détachement de la facturation: {e}")
        raise

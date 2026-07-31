# ============================================================
# ANALYSE : IAM DENY POLICY - PROTECTION CONTRE L'AUTO-ESCALADE
# ============================================================
# Ce fichier documente la tentative d'utilisation de IAM Deny Policies pour
# empêcher le SA Cloud Build de s'attribuer des rôles privilégiés, et explique
# pourquoi cette approche n'est PAS applicable.
#
# ============================================================
# PROBLÈME À RÉSOUDRE
# ============================================================
# Le SA Cloud Build (sa-cloudbuild@t-lexicon-231513.iam.gserviceaccount.com)
# possède roles/resourcemanager.projectIamAdmin (voir cloudbuild.tf lignes 228-256)
# qui lui permet de :
#
# 1. Créer/modifier/supprimer des IAM bindings au niveau projet
# 2. Gérer les IAM bindings sur les ressources (buckets, secrets, datasets)
# 3. Donner N'IMPORTE QUEL RÔLE à N'IMPORTE QUEL MEMBRE (y compris lui-même)
#
# RISQUE RÉSIDUEL :
# Le SA Cloud Build pourrait techniquement s'attribuer :
# - roles/owner → contrôle total du projet, y compris facturation et suppression
# - roles/editor → modification de toutes les ressources
# - roles/resourcemanager.projectIamAdmin → renforcer sa propre position
#
# IMPACT :
# Si le SA Cloud Build est compromis (ex: code malveillant injecté dans le repository),
# un attaquant pourrait escalader les privilèges avant d'être détecté.
#
# ============================================================
# TENTATIVE DE SOLUTION : IAM DENY POLICY
# ============================================================
# IAM Deny Policies fournissent une protection de sécurité en profondeur (defense in depth)
# car Deny Policy > Allow Policy : même si un principal a un rôle, la deny policy bloque.
#
# FONCTIONNEMENT THÉORIQUE :
# - Deny Policy au niveau projet
# - Utilise Common Expression Language (CEL) pour définir les conditions
# - Bloque des permissions spécifiques même si accordées par une Allow Policy
#
# ============================================================
# LIMITATION TECHNIQUE BLOQUANTE
# ============================================================
# IAM Deny Policies ne peuvent filtrer que sur :
# - denied_permissions : quelles permissions bloquer
# - denied_principals : à qui appliquer le blocage
#
# IMPOSSIBLE :
# - Filtrer sur les RÔLES CIBLES d'un binding IAM
# - Écrire "interdire de donner roles/owner à quiconque"
# - Écrire "autoriser setIamPolicy SAUF pour roles/owner, editor, projectIamAdmin"
#
# Les conditions CEL dans les Deny Policies n'ont PAS accès à :
# - protoPayload.serviceData.policyDelta.bindingDeltas.role (uniquement dans les logs)
# - request.member ou request.role (n'existent pas dans le contexte CEL)
#
# ALTERNATIVE TESTÉE ET REJETÉE :
# Bloquer complètement setIamPolicy au SA Cloud Build → CASSE LE PIPELINE TERRAFORM
# car Terraform a BESOIN de setIamPolicy pour gérer les bindings IAM des service accounts
# applicatifs (sa-scheduler, sa-workflow, sa-job-data, sa-job-nlp, sa-dashboard).
#
# ============================================================
# CONCLUSION
# ============================================================
# IAM Deny Policies ne sont PAS adaptées à ce cas d'usage car :
# 1. Impossible de filtrer sur "empêcher l'attribution de roles/owner à X"
# 2. Interdire setIamPolicy au SA Cloud Build casse le pipeline Terraform
# 3. Les conditions CEL ne permettent pas d'accéder aux rôles dans les bindings
#
# PREUVE : Provider Google 4.85.0 supporte google_iam_deny_policy (voir ci-dessous commenté)
# mais les limitations sont INHÉRENTES au service GCP IAM Deny Policies, pas au provider.

# resource "google_iam_deny_policy" "prevent_privilege_escalation" {
#   parent       = urlencode("cloudresourcemanager.googleapis.com/projects/${var.project_id}")
#   name         = "prevent-cloudbuild-setIamPolicy"
#   display_name = "Empêche le SA Cloud Build d'utiliser setIamPolicy"
#
#   rules {
#     description = "Empêche le SA Cloud Build de modifier les IAM policies"
#
#     deny_rule {
#       # Cible uniquement le SA Cloud Build
#       denied_principals = [
#         "principal://iam.googleapis.com/projects/${data.google_project.current.number}/serviceAccounts/${google_service_account.cloudbuild.email}",
#       ]
#
#       # Interdit setIamPolicy (nécessaire pour créer des bindings IAM)
#       # ATTENTION : Ceci CASSE le pipeline Terraform car il a besoin de cette permission
#       # pour gérer les bindings IAM des service accounts applicatifs
#       denied_permissions = [
#         "resourcemanager.projects.setIamPolicy",
#         "iam.serviceAccounts.setIamPolicy",
#         "storage.buckets.setIamPolicy",
#         "secretmanager.secrets.setIamPolicy",
#         "bigquery.datasets.setIamPolicy",
#       ]
#     }
#   }
# }

# ============================================================
# SOLUTION RETENUE : DÉTECTION + RÉPONSE (Defense in Depth)
# ============================================================
# Au lieu de PRÉVENIR (impossible avec Deny Policies), on DÉTECTE + RÉPOND
# via un système d'alerte basé sur les audit logs.
#
# IMPLÉMENTATION (voir monitoring.tf lignes 917-1072) :
#
# 1. ✅ Audit logs activés (terraform/audit.tf)
#    → Trace toutes les modifications IAM avec protoPayload.methodName="SetIamPolicy"
#
# 2. ✅ Log-based metric (google_logging_metric.iam_privilege_escalation)
#    → Filtre : protoPayload.serviceData.policyDelta.bindingDeltas.role in
#              ["roles/owner", "roles/editor", "roles/resourcemanager.projectIamAdmin"]
#    → Filtre : protoPayload.serviceData.policyDelta.bindingDeltas.action="ADD"
#    → Labels : principal (qui), role (quoi), member (à qui)
#
# 3. ✅ Alert policy (google_monitoring_alert_policy.iam_privilege_escalation)
#    → Se déclenche IMMÉDIATEMENT (threshold=0, duration=0s)
#    → Notification email vers guler.dilara2000@gmail.com
#    → Auto-close après 7 jours (laisse le temps d'investiguer)
#    → Documentation complète avec playbook de réponse
#
# AVANTAGES :
# ✅ Détection rapide (< 1 minute après la modification IAM)
# ✅ Pipeline Terraform reste fonctionnel
# ✅ Réponse humaine guidée (documentation dans l'alerte)
# ✅ Audit trail complet (logs + alerte + actions de remediation)
# ✅ Monitoring continu (pas de fenêtre de vulnérabilité)
#
# LIMITES ACCEPTÉES :
# ⚠️  Détection APRÈS l'événement (pas de prévention)
#     → Mitigé par : auto-close 7 jours, logs conservés 400 jours (audit.tf)
# ⚠️  Nécessite une intervention humaine pour révoquer
#     → Mitigé par : documentation claire, commandes gcloud prêtes à copier-coller
# ⚠️  Dépend de la disponibilité du canal de notification email
#     → Mitigé par : monitoring de l'uptime du dashboard (monitoring.tf)
#
# ============================================================
# ACCEPTATION DU RISQUE RÉSIDUEL
# ============================================================
# RISQUE : Le SA Cloud Build peut s'attribuer des rôles privilégiés.
#
# PROBABILITÉ : FAIBLE
# - Le SA Cloud Build n'est utilisé QUE par le pipeline CI/CD (pas par des humains)
# - Les builds sont déclenchés uniquement sur push main (code reviewé via PR)
# - Branch protection rules GitHub : require PR review avant merge (à configurer)
# - Le code Terraform est versionné et auditable (Git history)
#
# IMPACT SI EXPLOITÉ : ÉLEVÉ
# - Contrôle total du projet (roles/owner)
# - Modification/suppression de toutes les ressources
# - Accès aux secrets (anthropic-api-key, gemini-api-key)
# - Modification des données BigQuery
#
# MESURES COMPENSATOIRES :
# 1. Code review obligatoire (branch protection rules GitHub)
# 2. Audit logs activés avec rétention 400 jours (terraform/audit.tf)
# 3. Détection temps réel via log-based metric + alerting policy (monitoring.tf)
# 4. Documentation claire du risque (ce fichier)
# 5. Rôles Cloud Build réduits au strict nécessaire (cloudbuild.tf lignes 61-241)
# 6. Condition IAM sur serviceAccountAdmin (restreint au préfixe sa-)
#
# ACCEPTÉ PAR : [À remplir : Nom du responsable sécurité / Lead Tech]
# DATE : [À remplir]
# REVUE PRÉVUE : Trimestrielle (vérifier si une alternative technique existe)
#
# ============================================================
# ALTERNATIVES FUTURES À CONSIDÉRER
# ============================================================
# Si GCP ajoute des fonctionnalités permettant de filtrer sur les rôles cibles :
# - Deny Policy avec condition CEL sur request.binding.role
# - Organization Policy Constraint custom sur IAM bindings
# - IAM Conditions sur projectIamAdmin (filtrer par rôle cible)
#
# Veille technologique :
# - https://cloud.google.com/iam/docs/deny-overview
# - https://cloud.google.com/iam/docs/conditions-overview
# - https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints

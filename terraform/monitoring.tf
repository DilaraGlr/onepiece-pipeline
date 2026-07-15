# ============================================================
# MONITORING & ALERTING
# ============================================================
# Configuration des canaux de notification pour les alertes

# ============================================================
# NOTIFICATION CHANNEL - EMAIL
# ============================================================
# Canal de notification par email pour recevoir les alertes
# du projet (erreurs, budgets, incidents)

resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Dilara"
  type         = "email"

  labels = {
    email_address = "guler.dilara2000@gmail.com"
  }

  enabled = true
}

# ============================================================
# OUTPUTS
# ============================================================

output "notification_channel_email" {
  description = "ID du canal de notification email"
  value       = google_monitoring_notification_channel.email.id
}

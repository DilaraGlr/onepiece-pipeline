-- ============================================================
-- ANALYSE DES ÉCHECS PAR JOB ET PAR SEMAINE
-- ============================================================
-- Cette requête analyse les logs des Cloud Run jobs stockés dans
-- le dataset pipeline_logs pour identifier les échecs par job
-- et par semaine sur les 3 derniers mois.
--
-- Utilisation:
-- Remplacer `t-lexicon-231513` par votre project_id si différent
-- ============================================================

WITH logs_recents AS (
  SELECT
    timestamp,
    severity,
    resource.labels.job_name AS job_name,
    textPayload,
    jsonPayload
  FROM
    `t-lexicon-231513.pipeline_logs.cloud_run_job_*`
  WHERE
    -- Filtrer sur les 3 derniers mois
    timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 MONTH)
    -- Filtrer uniquement les logs d'erreur (ERROR, CRITICAL, ALERT, EMERGENCY)
    AND severity >= 'ERROR'
    -- Filtrer sur nos 3 jobs
    AND resource.labels.job_name IN (
      'onepiece-scraper-job',
      'ocr-pipeline-job',
      'nlp-pipeline-job'
    )
)

SELECT
  -- Semaine (début de semaine = lundi)
  TIMESTAMP_TRUNC(timestamp, WEEK(MONDAY)) AS semaine,

  -- Nom du job
  job_name,

  -- Nombre d'erreurs
  COUNT(*) AS nombre_erreurs,

  -- Répartition par niveau de sévérité
  COUNTIF(severity = 'ERROR') AS erreurs,
  COUNTIF(severity = 'CRITICAL') AS critical,
  COUNTIF(severity IN ('ALERT', 'EMERGENCY')) AS alert_emergency,

  -- Premier et dernier échec de la semaine
  MIN(timestamp) AS premier_echec,
  MAX(timestamp) AS dernier_echec

FROM
  logs_recents

GROUP BY
  semaine,
  job_name

ORDER BY
  semaine DESC,
  nombre_erreurs DESC,
  job_name

-- ============================================================
-- NOTES D'UTILISATION
-- ============================================================
-- 1. Si aucun résultat, vérifier le nom de la table dans pipeline_logs:
--    SELECT table_name FROM `t-lexicon-231513.pipeline_logs.INFORMATION_SCHEMA.TABLES`
--
-- 2. Pour voir tous les logs (pas seulement les erreurs):
--    Retirer la condition "AND severity >= 'ERROR'"
--
-- 3. Pour changer la période:
--    Modifier INTERVAL 3 MONTH (ex: INTERVAL 1 MONTH, INTERVAL 6 MONTH)
--
-- 4. Pour regrouper par jour au lieu de semaine:
--    Remplacer TIMESTAMP_TRUNC(timestamp, WEEK(MONDAY)) par TIMESTAMP_TRUNC(timestamp, DAY)
-- ============================================================

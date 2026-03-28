# TODO — onepiece-pipeline

Liste des problèmes connus et améliorations à faire.

---

## ✅ Terminé

- [x] Scraper onepiecescan.fr (1172 chapitres en français)
- [x] Chargement dans BigQuery avec `load_table_from_json`
- [x] Dashboard Streamlit avec graphiques Plotly
- [x] Docker (image AMD64 pour Cloud Run)
- [x] Cloud Run Job
- [x] Cloud Workflows + Cloud Scheduler (chaque lundi 9h)
- [x] Terraform (infrastructure as code)

---

## 🔴 Bugs à corriger

- [ ] **Warning OpenSSL au lancement du scraper en local**
  ```
  NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
  ```
  Lié à Python 3.9 sur Mac. Ne bloque pas le fonctionnement.
  → Régler en mettant Python à jour ou en downgradant urllib3.

- [ ] **Cloud Workflows — temps d'attente fixe**
  On attend 1500 secondes (25 min) au lieu de vraiment vérifier
  si le job est terminé.
  → Implémenter un polling qui vérifie l'état du job toutes les 30s.

---

## 🟡 Améliorations à faire

- [ ] **Dashboard — design à peaufiner**
  Le thème One Piece est en place mais peut être amélioré.
  → Retravailler les couleurs et la mise en page.

- [ ] **Dashboard — ajouter des stats sur les images**
  On a les URLs des images mais on ne les affiche pas encore.
  → Ajouter un graphique sur le nombre d'images par chapitre au fil du temps.

- [ ] **Scraper — ajouter la gestion des erreurs réseau**
  Si onepiecescan.fr est indisponible, le scraper plante.
  → Ajouter un retry automatique avec `time.sleep` entre les tentatives.

- [ ] **Scraper — détecter uniquement les nouveaux chapitres**
  Actuellement on scrape tous les 1172 chapitres à chaque exécution.
  → Comparer avec BigQuery pour ne récupérer que les chapitres manquants.

---

## 🔵 Prochaines étapes (avancées)

- [ ] **OCR — extraire le texte des bulles**
  Télécharger les images et utiliser un outil OCR pour extraire
  les dialogues. Permettra des stats sur les personnages.

- [ ] **Déployer le dashboard en ligne**
  Actuellement le dashboard tourne seulement en local.
  → Déployer sur Streamlit Cloud ou Cloud Run pour y accéder partout.
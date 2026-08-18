"""
Utilitaires communs pour les pipelines One Piece.
"""

import time


def retry_with_backoff(func, *args, max_retries=3, operation_name="opération", **kwargs):
    """
    Exécute une fonction avec retry et backoff exponentiel.
    Pattern identique à request_with_retry() du scraper.

    Args:
        func: Fonction à exécuter
        *args: Arguments positionnels pour la fonction
        max_retries: Nombre maximum de tentatives (défaut: 3)
        operation_name: Nom de l'opération pour les logs
        **kwargs: Arguments nommés pour la fonction

    Returns:
        Résultat de la fonction si succès

    Raises:
        Exception: Si toutes les tentatives échouent ou erreur définitive
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)

            # Erreurs définitives (pas de retry)
            if any(keyword in error_msg.lower() for keyword in [
                "authentication", "unauthorized", "forbidden",
                "invalid", "not found", "400", "401", "403", "404"
            ]):
                print(f"  ❌ Erreur définitive ({operation_name}) : {error_msg}")
                raise

            # Dernière tentative échouée
            if attempt == max_retries - 1:
                print(f"  ❌ Échec après {max_retries} tentatives ({operation_name}) : {error_msg}")
                raise

            # Retry sur erreur temporaire
            wait = 5 * (2 ** attempt)
            print(
                f"  🔄 Tentative {attempt + 1}/{max_retries} échouée "
                f"({operation_name}), retry dans {wait}s... ({error_msg})"
            )
            time.sleep(wait)

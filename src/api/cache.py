"""
Cache mémoire simple avec TTL pour les données rarement modifiées.
"""
import time
from typing import Any, Optional


class TTLCache:
    """Cache en mémoire avec expiration par clé."""

    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: Durée de vie par défaut en secondes (5 min).
        """
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache si elle n'a pas expiré."""
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Stocke une valeur dans le cache."""
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (value, time.monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        """Supprime une clé du cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Vide tout le cache."""
        self._store.clear()


# Instance globale partagée entre les routers
cache = TTLCache(default_ttl=300)

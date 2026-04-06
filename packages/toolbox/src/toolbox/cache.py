import datetime as dt
from abc import ABC, abstractmethod

from loguru import logger

__all__ = ("TTLCache",)


class TTLCache[KT, VT](ABC):
    _ttl: dt.timedelta

    def __init__(self, **ttl: float) -> None:
        """Keyword arguments are passed to datetime.timedelta."""
        self._ttl = dt.timedelta(**ttl)
        self._cache: dict[KT, tuple[dt.datetime, VT]] = {}

    def __contains__(self, key: KT) -> bool:
        return key in self._cache

    def __getitem__(self, key: KT) -> tuple[dt.datetime, VT]:
        return self._cache[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        self._cache[key] = (dt.datetime.now(tz=dt.UTC), value)

    @abstractmethod
    async def fetch(self, key: KT) -> None:
        pass

    def _prune_expired_keys(self) -> None:
        cache_name = type(self).__name__
        now = dt.datetime.now(tz=dt.UTC)
        for key in {
            key
            for key, (timestamp, _) in self._cache.items()
            if now - timestamp >= self._ttl
        }:
            logger.debug(
                "dropping expired {cache} key {key!r}", cache=cache_name, key=key
            )
            del self._cache[key]

    async def get(self, key: KT) -> VT | None:
        self._prune_expired_keys()
        if key not in self:
            logger.debug("{key} not in cache; fetching", key=key)
            await self.fetch(key)
        try:
            _, value = self[key]
        except KeyError:
            return None
        return value

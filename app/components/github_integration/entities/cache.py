from contextlib import suppress
from typing import final, override

from githubkit.exception import RequestFailed
from loguru import logger

from .discussions import get_discussion
from app.components.github_integration.models import (
    Entity,
    EntitySignature,
    Issue,
    PullRequest,
)
from app.config import gh
from toolbox.cache import TTLCache


async def get_issue_or_pr(key: EntitySignature) -> Issue | PullRequest | None:
    with suppress(RequestFailed):
        entity = (await gh().rest.issues.async_get(*key)).parsed_data
        if entity.pull_request:
            return await get_pr(key)
        return Issue.model_validate(entity, from_attributes=True)
    return None


async def get_pr(key: EntitySignature) -> PullRequest | None:
    with suppress(RequestFailed):
        resp = await gh().rest.pulls.async_get(*key)
        return PullRequest.model_validate(resp.parsed_data, from_attributes=True)
    return None


@final
class EntityCache(TTLCache[tuple[EntitySignature, str | None], Entity]):
    @override
    async def fetch(self, key: tuple[EntitySignature, str | None]) -> None:
        key_, kind_hint = key
        unhinted_key = key_, None
        if kind_hint == "pull" and (pull := await get_pr(key_)):
            self[unhinted_key] = pull
        elif kind_hint == "discussions" and (discussion := await get_discussion(*key_)):
            self[unhinted_key] = discussion
        elif issue_or_pr := await get_issue_or_pr(key_):
            self[unhinted_key] = issue_or_pr
        elif discussion := await get_discussion(*key_):
            self[unhinted_key] = discussion

    @override
    async def get(self, key: tuple[EntitySignature, str | None]) -> Entity | None:
        unhinted_key = key[0], None
        if unhinted_key not in self:
            logger.debug("{key} not in cache; fetching", key=key)
            await self.fetch(key)
        try:
            _, value = self[unhinted_key]
        except KeyError:
            return None
        return value


entity_cache = EntityCache(minutes=30)

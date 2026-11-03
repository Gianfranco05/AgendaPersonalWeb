"""Consulta del buscador global.

Una consulta por fuente, en serie sobre la misma sesion (una `AsyncSession` no
admite consultas concurrentes y son como mucho ~20, chicas y acotadas por el
indice de `user_id`). Cada consulta filtra por `user_id` ANTES que por texto.
"""
from typing import Any, Optional, Sequence

from sqlalchemy import and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.buscador.highlight import highlight_ranges, make_snippet
from app.modules.buscador.normalize import LIKE_ESCAPE, escape_like, fold, fold_text, tokenize
from app.modules.buscador.schemas import SearchGroup, SearchItem, SearchResponse
from app.modules.buscador.sources import SEARCH_SOURCES, TYPE_LABELS, TYPE_ORDER, SearchSource
from app.modules.modulos.service import ModulesService


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def allowed_types(self, user_id: str) -> set[str]:
        """Tipos en los que este usuario puede buscar (base + plantillas activas)."""
        keys = await ModulesService(self.db).searchable_module_keys(user_id)
        return {s.type for s in SEARCH_SOURCES if s.module_key in keys}

    async def search(
        self, user_id: str, q: str, types: Sequence[str], limit: int
    ) -> SearchResponse:
        """`q` crudo: se normaliza aca. Levanta `QueryError` si no es valida."""
        cleaned, tokens = tokenize(q)
        allowed = await self.allowed_types(user_id)
        wanted = [t for t in TYPE_ORDER if t in types and t in allowed]

        groups: list[SearchGroup] = []
        for type_ in wanted:
            rows: list[tuple[int, str, str, SearchItem]] = []
            has_more = False
            for source in (s for s in SEARCH_SOURCES if s.type == type_):
                found, more = await self._run_source(source, user_id, cleaned, tokens, limit)
                rows.extend(found)
                has_more = has_more or more
            if not rows:
                continue
            # Varias entidades del mismo tipo (materias + examenes): se mezclan
            # respetando el orden (rango, fecha desc, id) y el limite del grupo.
            rows.sort(key=lambda r: r[3].id)
            rows.sort(key=lambda r: r[2], reverse=True)
            rows.sort(key=lambda r: r[0])
            if len(rows) > limit:
                has_more = True
            groups.append(
                SearchGroup(
                    type=type_,
                    label=TYPE_LABELS[type_],
                    has_more=has_more,
                    items=[r[3] for r in rows[:limit]],
                )
            )
        return SearchResponse(query=cleaned, groups=groups)

    async def _run_source(
        self, source: SearchSource, user_id: str, query: str, tokens: list[str], limit: int
    ) -> tuple[list[tuple[int, str, str, SearchItem]], bool]:
        model = source.model
        fields = [source.title_col, *source.content_cols]
        patterns = [f"%{escape_like(t)}%" for t in tokens]

        token_clauses = []
        for tok_pattern in patterns:
            options = [fold(c).like(tok_pattern, escape=LIKE_ESCAPE) for c in fields]
            if source.token_match is not None:
                options.append(source.token_match(tok_pattern, user_id))
            token_clauses.append(or_(*options))

        phrase = f"{escape_like(fold_text(query))}%"
        title = fold(source.title_col)
        rank = case(
            (title.like(phrase, escape=LIKE_ESCAPE), 0),
            (and_(*[title.like(p, escape=LIKE_ESCAPE) for p in patterns]), 1),
            else_=2,
        )

        stmt = (
            select(model, rank.label("rank"))
            .where(model.user_id == user_id, *source.extra_where, *token_clauses)
            .order_by(rank, source.date_expr.desc(), model.id)
            .limit(limit + 1)
        )
        result = await self.db.execute(stmt)
        fetched = result.all()
        has_more = len(fetched) > limit
        fetched = fetched[:limit]

        objs = [row[0] for row in fetched]
        ctx: dict[str, Any] = {}
        if source.enrich is not None and objs:
            ctx = await source.enrich(self.db, user_id, objs)

        out: list[tuple[int, str, str, SearchItem]] = []
        for obj, rank_value in fetched:
            data = source.to_item(obj, ctx)
            snippet_cols = source.snippet_cols or source.content_cols
            snippet, snippet_ranges = make_snippet(
                [getattr(obj, c.key, None) for c in snippet_cols], tokens
            )
            parent_id = data.parent_id
            item = SearchItem(
                id=obj.id,
                type=source.type,
                entity=source.entity,
                title=data.title,
                title_highlights=highlight_ranges(data.title, tokens),
                snippet=snippet,
                snippet_highlights=snippet_ranges,
                date=data.date,
                parent_id=parent_id,
                path=source.path_for(obj.id, parent_id),
                meta=data.meta,
            )
            out.append((int(rank_value), item.id, data.date or "", item))
        return out, has_more

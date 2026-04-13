"""Search backend abstraction and PostgreSQL full-text search implementation.

The SearchBackend ABC allows swapping Postgres FTS for Meilisearch (or another
engine) without touching routers or frontend code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class SearchResult:
    page_id: UUID
    title: str
    snippet: str
    collection_id: UUID
    space_id: UUID
    space_name: str
    collection_name: str
    rank: float


class SearchBackend(ABC):
    @abstractmethod
    def search(
        self,
        workspace_id: UUID,
        query: str,
        db: Session,
        *,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search pages within a workspace. Returns ranked results."""
        ...


class PostgresSearchBackend(SearchBackend):
    """Full-text search using PostgreSQL tsvector + GIN index."""

    def search(
        self,
        workspace_id: UUID,
        query: str,
        db: Session,
        *,
        limit: int = 20,
    ) -> list[SearchResult]:
        if not query.strip():
            return self._browse(workspace_id, db, limit=limit)
        return self._ranked_search(workspace_id, query.strip(), db, limit=limit)

    def _browse(
        self,
        workspace_id: UUID,
        db: Session,
        *,
        limit: int,
    ) -> list[SearchResult]:
        """Return all pages in the workspace ordered by most recently revised."""
        sql = text("""
            SELECT
                p.id AS page_id,
                p.title,
                '' AS snippet,
                p.collection_id,
                s.id AS space_id,
                s.name AS space_name,
                c.name AS collection_name,
                0.0 AS rank
            FROM pages p
            JOIN revisions r ON r.id = p.current_revision_id
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :workspace_id
            ORDER BY r.created_at DESC
            LIMIT :limit
        """)
        rows = db.execute(sql, {"workspace_id": workspace_id, "limit": limit}).fetchall()
        return [self._row_to_result(row) for row in rows]

    def _ranked_search(
        self,
        workspace_id: UUID,
        query: str,
        db: Session,
        *,
        limit: int,
    ) -> list[SearchResult]:
        """Title ILIKE match ranked first, FTS body match as secondary signal."""
        sql = text("""
            SELECT
                p.id AS page_id,
                p.title,
                CASE
                    WHEN p.search_vector @@ plainto_tsquery('english', :query)
                    THEN ts_headline(
                        'english',
                        r.content,
                        plainto_tsquery('english', :query),
                        'StartSel=**, StopSel=**, MaxWords=35, MinWords=15'
                    )
                    ELSE ''
                END AS snippet,
                p.collection_id,
                s.id AS space_id,
                s.name AS space_name,
                c.name AS collection_name,
                CASE WHEN p.title ILIKE :title_pattern THEN 1 ELSE 0 END
                    + ts_rank(p.search_vector, plainto_tsquery('english', :query))
                    AS rank
            FROM pages p
            JOIN revisions r ON r.id = p.current_revision_id
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :workspace_id
              AND (
                  p.title ILIKE :title_pattern
                  OR p.search_vector @@ plainto_tsquery('english', :query)
              )
            ORDER BY rank DESC, r.created_at DESC
            LIMIT :limit
        """)
        rows = db.execute(
            sql,
            {
                "workspace_id": workspace_id,
                "query": query,
                "title_pattern": f"%{query}%",
                "limit": limit,
            },
        ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row) -> "SearchResult":
        return SearchResult(
            page_id=row.page_id,
            title=row.title,
            snippet=row.snippet,
            collection_id=row.collection_id,
            space_id=row.space_id,
            space_name=row.space_name,
            collection_name=row.collection_name,
            rank=row.rank,
        )

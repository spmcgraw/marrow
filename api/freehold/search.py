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
        sql = text("""
            SELECT
                p.id AS page_id,
                p.title,
                ts_headline(
                    'english',
                    r.content,
                    plainto_tsquery('english', :query),
                    'StartSel=**, StopSel=**, MaxWords=35, MinWords=15'
                ) AS snippet,
                p.collection_id,
                s.id AS space_id,
                s.name AS space_name,
                c.name AS collection_name,
                ts_rank(p.search_vector, plainto_tsquery('english', :query)) AS rank
            FROM pages p
            JOIN revisions r ON r.id = p.current_revision_id
            JOIN collections c ON c.id = p.collection_id
            JOIN spaces s ON s.id = c.space_id
            WHERE s.workspace_id = :workspace_id
              AND p.search_vector @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)

        rows = db.execute(
            sql,
            {"workspace_id": workspace_id, "query": query, "limit": limit},
        ).fetchall()

        return [
            SearchResult(
                page_id=row.page_id,
                title=row.title,
                snippet=row.snippet,
                collection_id=row.collection_id,
                space_id=row.space_id,
                space_name=row.space_name,
                collection_name=row.collection_name,
                rank=row.rank,
            )
            for row in rows
        ]

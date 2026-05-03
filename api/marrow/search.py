"""Search backend abstraction and PostgreSQL full-text search implementation.

The SearchBackend ABC allows swapping Postgres FTS for Meilisearch (or another
engine) without touching routers or frontend code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class SearchResult:
    node_id: UUID
    name: str
    snippet: str
    space_id: UUID
    space_name: str
    node_path: list[str]
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


# Recursive CTE fragment that resolves the ordered ancestor folder names for a
# given node. Yields one row with an `ancestors` text[] column (root → leaf).
_ANCESTOR_PATH_CTE = """
    WITH RECURSIVE anc(nm, parent_id, depth) AS (
        SELECT p.name, p.parent_id, 1
        FROM nodes p
        WHERE p.id = n.parent_id
        UNION ALL
        SELECT p2.name, p2.parent_id, a.depth + 1
        FROM nodes p2
        JOIN anc a ON p2.id = a.parent_id
    )
    SELECT ARRAY(SELECT nm FROM anc ORDER BY depth DESC)
"""


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
        sql = text(f"""
            SELECT
                n.id AS node_id,
                n.name,
                '' AS snippet,
                s.id AS space_id,
                s.name AS space_name,
                COALESCE(
                    ({_ANCESTOR_PATH_CTE}),
                    ARRAY[]::text[]
                ) AS node_path,
                0.0 AS rank
            FROM nodes n
            JOIN revisions r ON r.id = n.current_revision_id
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :workspace_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
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
        """Name ILIKE match ranked first, FTS body match as secondary signal."""
        sql = text(f"""
            SELECT
                n.id AS node_id,
                n.name,
                CASE
                    WHEN n.search_vector @@ plainto_tsquery('english', :query)
                    THEN ts_headline(
                        'english',
                        r.content,
                        plainto_tsquery('english', :query),
                        'StartSel=**, StopSel=**, MaxWords=35, MinWords=15'
                    )
                    ELSE ''
                END AS snippet,
                s.id AS space_id,
                s.name AS space_name,
                COALESCE(
                    ({_ANCESTOR_PATH_CTE}),
                    ARRAY[]::text[]
                ) AS node_path,
                CASE WHEN n.name ILIKE :name_pattern THEN 1 ELSE 0 END
                    + ts_rank(n.search_vector, plainto_tsquery('english', :query))
                    AS rank
            FROM nodes n
            JOIN revisions r ON r.id = n.current_revision_id
            JOIN spaces s ON s.id = n.space_id
            WHERE s.workspace_id = :workspace_id
              AND n.type = 'page'
              AND n.deleted_at IS NULL
              AND (
                  n.name ILIKE :name_pattern
                  OR n.search_vector @@ plainto_tsquery('english', :query)
              )
            ORDER BY rank DESC, r.created_at DESC
            LIMIT :limit
        """)
        rows = db.execute(
            sql,
            {
                "workspace_id": workspace_id,
                "query": query,
                "name_pattern": f"%{query}%",
                "limit": limit,
            },
        ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row) -> "SearchResult":
        return SearchResult(
            node_id=row.node_id,
            name=row.name,
            snippet=row.snippet,
            space_id=row.space_id,
            space_name=row.space_name,
            node_path=list(row.node_path) if row.node_path else [],
            rank=row.rank,
        )

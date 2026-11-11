"""Select a stable set of curated anchors for an interview."""
import secrets


class QuestionBankUnavailable(ValueError):
    """The bank cannot provide all topics for the requested interview."""


class QuestionBankService:
    def __init__(self, repository):
        self.repository = repository

    async def select(self, focus: str, language: str, role: str, level: str, count: int = 5) -> list[dict]:
        rows = await self.repository.list_question_bank(focus, language)
        role, level = role.strip().casefold(), level.strip().casefold()
        selected, used_keys = [], set()
        for topic in range(count):
            candidates = [row for row in rows if row["topic_index"] == topic
                          and row["key"] not in used_keys and row["role"].casefold() in ("*", role)
                          and row["level"].casefold() in ("*", level)]
            if not candidates:
                raise QuestionBankUnavailable(f"Question bank has no {focus}/{language} entry for topic {topic + 1}")
            latest = {}
            for row in candidates:
                if row["key"] not in latest or row["version"] > latest[row["key"]]["version"]:
                    latest[row["key"]] = row
            weighted = [row for row in latest.values() for _ in range(
                1 + 2 * (row["role"] != "*") + 2 * (row["level"] != "*"))]
            row = secrets.choice(weighted)
            used_keys.add(row["key"])
            selected.append({key: row[key] for key in
                             ("key", "version", "language", "question", "criteria", "source_url", "provenance")})
        return selected

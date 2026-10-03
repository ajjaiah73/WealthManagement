from app.domain.advisory import AdvisoryCaseRecord


class InMemoryCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[str, AdvisoryCaseRecord] = {}

    def get(self, case_id: str) -> AdvisoryCaseRecord | None:
        return self._cases.get(case_id)

    def list(self) -> list[AdvisoryCaseRecord]:
        return sorted(self._cases.values(), key=lambda r: r.case.created_at)

    def save(self, record: AdvisoryCaseRecord) -> AdvisoryCaseRecord:
        self._cases[record.case.case_id] = record
        return record

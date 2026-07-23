from finapp.application.import_transactions import import_csv
from finapp.infrastructure.repositories import InMemoryTransactionRepository


def test_import_csv_persists_valid_rows_and_reports_invalid_ones() -> None:
    content = (
        b"date,description,amount,category\n"
        b"2026-01-01,Salary,2500,Income\n"
        b"2026-01-02,Coffee,-4.5,Food\n"
        b"2026-01-03,Bad,0,Misc\n"
    )
    repository = InMemoryTransactionRepository()

    result = import_csv(content, repository)

    assert result.imported_count == 2
    assert result.errors[0].row_number == 4
    assert [item.description for item in repository.list_all()] == ["Salary", "Coffee"]


def test_import_csv_rejects_missing_required_columns() -> None:
    repository = InMemoryTransactionRepository()

    try:
        import_csv(b"date,amount\n2026-01-01,10\n", repository)
    except ValueError as error:
        assert "description" in str(error)
    else:
        raise AssertionError("Expected a missing-column error")

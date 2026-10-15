from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes


def test_identical_documents_have_no_differences() -> None:
    document = parse_bytes(b"[A]\r\nValues=1 2 3\r\n")

    assert diff_documents(document, document) == []


def test_diff_reports_changed_value_token() -> None:
    before = parse_bytes(b"[A]\r\nValues=1 2 3\r\n")
    after = parse_bytes(b"[A]\r\nValues=1 9 3\r\n")

    differences = diff_documents(before, after)

    assert differences == [
        {
            "kind": "value_token_changed",
            "section": "A",
            "section_occurrence": 0,
            "key": "Values",
            "key_occurrence": 0,
            "token_index": 1,
            "before": "2",
            "after": "9",
        }
    ]


def test_diff_preserves_repeated_key_occurrences() -> None:
    before = parse_bytes(b"[A]\nK=one\nK=two\n")
    after = parse_bytes(b"[A]\nK=one\nK=changed\n")

    differences = diff_documents(before, after)

    assert differences[0]["key_occurrence"] == 1


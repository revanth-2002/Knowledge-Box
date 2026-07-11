from app.services.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "hello world this is a short note"
    chunks = chunk_text(text, chunk_size=50, overlap=5)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].index == 0


def test_long_text_produces_overlapping_chunks():
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=20, overlap=5)

    assert len(chunks) > 1
    # consecutive chunks overlap by the configured amount
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-5:] == second_words[:5]

    # indices are sequential starting at 0
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunk_size_must_exceed_overlap():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=10, overlap=10)


def test_all_words_are_covered():
    words = [f"w{i}" for i in range(37)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap=2)

    covered = set()
    for c in chunks:
        covered.update(c.text.split())
    assert covered == set(words)

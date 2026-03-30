from rag import split_into_chunks


def test_split_into_chunks_empty():
    assert split_into_chunks("") == []


def test_split_into_chunks_single_small():
    words = " ".join([f"w{i}" for i in range(50)])
    chunks = split_into_chunks(words, chunk_words=400, overlap=50)
    assert len(chunks) == 1


def test_split_into_chunks_many_words():
    words = " ".join([f"w{i}" for i in range(900)])
    chunks = split_into_chunks(words, chunk_words=400, overlap=50)
    assert len(chunks) >= 2

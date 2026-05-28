from mentask.core.constraints import FileReadingSession, ReadFileConstraint


def test_constraint_detects_large_file():
    constraint = ReadFileConstraint.check_request(total_lines=5000, existing_line_offset=1)
    assert constraint["strategy"] == "chunked"
    assert constraint["chunk_size"] == 500


def test_constraint_full_strategy_for_small_file():
    constraint = ReadFileConstraint.check_request(total_lines=50)
    assert constraint["strategy"] == "full"
    assert constraint["size"] == 50


def test_session_tracks_progress():
    session = FileReadingSession("dummy.txt", total_lines=100)
    session.add_chunk(1, 10, "chunk data")
    assert session.current_offset == 11
    assert session.metrics["total_chunks_read"] == 1


def test_session_detects_loop_after_3_attempts():
    session = FileReadingSession("dummy.txt", total_lines=500)
    session.add_chunk(1, 10, "chunk1")

    # Simulate repeated identical chunks
    session.mark_attempt()
    assert session.should_retry() is True

    session.mark_attempt()
    assert session.should_retry() is True

    session.mark_attempt()
    assert session.should_retry() is False

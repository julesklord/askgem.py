from src.askgem.core.summarizer import Summarizer


def test_format_summary_with_tags():
    raw = """
<analysis>
I should summarize this.
</analysis>
<summary>
1. Request: Fix bug.
2. Status: Done.
</summary>
"""
    formatted = Summarizer.format_summary(raw)
    assert "I should summarize this" not in formatted
    assert "Request: Fix bug" in formatted
    assert "<summary>" not in formatted

def test_format_summary_plain_text():
    raw = "Just a plain summary without tags."
    formatted = Summarizer.format_summary(raw)
    assert formatted == "Just a plain summary without tags."

def test_get_user_continuation_message():
    summary = "Project status: half done."
    msg = Summarizer.get_user_continuation_message(summary)
    assert "SUMMARY:" in msg
    assert summary in msg
    assert "Continue the conversation" in msg

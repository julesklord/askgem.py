import re


class Summarizer:
    """Handles LLM-based conversation summarization to drastically reduce token usage."""

    BASE_SUMMARIZATION_PROMPT = """
CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.
Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.

Before providing your final summary, wrap your analysis in <analysis> tags to organize your thoughts and ensure you've covered all necessary points. In your analysis process:
1. Chronologically analyze each message and section of the conversation.
2. Identify user requests, technical decisions, file edits, and errors encountered.
3. Double-check for technical accuracy.

Your summary should include the following sections:
1. Primary Request and Intent: Capture all of the user's explicit requests.
2. Key Technical Concepts: List important technical concepts and frameworks discussed.
3. Files and Code Sections: Enumerate specific files examined, modified, or created. Include full code snippets where applicable.
4. Errors and fixes: List all errors that you ran into, and how you fixed them.
5. All user messages: List ALL user messages that are not tool results.
6. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on.
7. Current Work: Describe in detail precisely what was being worked on immediately before this summary request.
8. Optional Next Step: List the next step that you will take.

Example structure:
<analysis>
[Your thought process]
</analysis>

<summary>
1. Primary Request and Intent: [Description]
2. Key Technical Concepts: [List]
3. Files and Code Sections: [List with snippets]
...
</summary>
"""

    @staticmethod
    def format_summary(raw_response: str) -> str:
        """Strips <analysis> blocks and formats the <summary> for context injection."""
        # Strip the analysis part
        summary_content = re.sub(r"<analysis>[\s\S]*?<\/analysis>", "", raw_response)

        # Extract content inside <summary> if present, or take the whole thing
        match = re.search(r"<summary>([\s\S]*?)<\/summary>", summary_content)
        if match:
            summary_content = match.group(1).strip()
        else:
            # If tags are missing but text exists, just clean it up
            summary_content = summary_content.replace("<summary>", "").replace("</summary>", "").strip()

        return summary_content

    @staticmethod
    def get_user_continuation_message(summary: str) -> str:
        """Wraps the summary in a message that instructs the model on how to continue."""
        return f"""
This session is being continued from a previous conversation that ran out of context.
The summary below covers the earlier portion of the conversation.

SUMMARY:
{summary}

Continue the conversation from where it left off without asking the user any further questions.
Resume directly — do not acknowledge the summary, do not recap what was happening.
Pick up the last task as if the break never happened.
""".strip()

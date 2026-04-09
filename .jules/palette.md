## 2025-04-05 - [Add Busy State to Input in TUI]
**Learning:** In TUI applications using Textual, interactive widgets like `Input` should be explicitly disabled during asynchronous operations (like streaming an AI response). This provides immediate visual feedback of the "busy" state and prevents users from accidentally submitting concurrent inputs, which reduces cognitive load and prevents race conditions.
**Action:** Always disable inputs during async agent turns, and remember to re-enable and explicitly refocus them in a `finally` block to restore usability once the process completes.

## 2025-05-18 - [Add Busy State during Application Initialization]
**Learning:** Application startup sequences in Textual applications can lead to race conditions if the inputs are not explicitly disabled before they have fully loaded. Since `init_api` performs network calls and loads chat history asynchronously, it can result in inputs being processed before initialization completes.
**Action:** Always explicitly disable interactive inputs at the beginning of asynchronous initialization sequences and remember to re-enable and explicitly refocus them inside a `finally` block.
## 2026-04-07 - [Preserve Error Visual Feedback]
**Learning:** When resetting TUI widget states (like 'idle') in a `finally` block after an asynchronous operation, conditionally check that the state isn't already set to 'error'. Blindly resetting state clears critical visual error feedback, confusing users.
**Action:** Always verify the current state is not 'error' before reverting a widget to 'idle' during a cleanup/finally phase.

## 2026-04-09 - [Add Visual Loading State to Placeholder]
**Learning:** Disabling an input field during async operations prevents interaction, but doesn't clearly communicate *why* it's disabled. Changing the input's placeholder text to a 'thinking/loading' message provides immediate, intuitive feedback.
**Action:** Always update placeholder text to indicate a loading state alongside disabling inputs during async operations, and ensure it's reverted in the finally block.

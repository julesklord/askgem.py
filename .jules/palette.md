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

## 2026-04-10 - [Localize UI State Text]
**Learning:** Hardcoding UI strings (like "AskGem está pensando..." or "Escribe tu mensaje...") during runtime state changes breaks internationalization (i18n) and can result in confusing UX where the application language spontaneously changes based on the state. Additionally, initializing a chat input with an incorrect default placeholder (e.g., "Please enter your API Key") creates a confusing first impression.
**Action:** Always use the localization function (e.g., `_("dashboard.prompt_thinking")`) when updating UI text dynamically during async operations, and ensure new state strings are properly defined across the supported locale JSON files.

## 2026-04-11 - [Disable Input Widget During Slash Commands]
**Learning:** During mid-conversation slash commands, if the input widget is not disabled, users can type concurrent inputs which might lead to unexpected states or race conditions while the asynchronous operation completes. Providing visual feedback (like a thinking placeholder) makes the app feel more responsive and prevents users from feeling stuck or frustrated.
**Action:** Always disable inputs during async agent operations, including local mid-conversation slash commands, and ensure they are re-enabled and explicitily refocused in a `finally` block to restore usability once the process completes.

## 2026-04-12 - [Localize UI State Text in Dashboard]
**Learning:** Hardcoding UI strings (like "Cargando..." or "Misión Actual") directly in UI components breaks internationalization, particularly for non-Spanish users, resulting in a mixed-language interface.
**Action:** Always extract text visible in the UI and use the internationalization system (`_()`) to fetch localized strings defined in the JSON locale files, ensuring consistency across languages.

## 2026-04-12 - [Add Tooltips to TUI Inputs]
**Learning:** Textual widgets (such as `Input`) support the `tooltip` attribute, which provides an unobtrusive way to offer hints and keyboard shortcuts without cluttering the UI. When adding tooltips, they must be properly localized by hooking into the `en.json` and `es.json` files and using the `_()` localization function during widget initialization, rather than hardcoding the strings.
**Action:** Always consider adding localized `tooltip` attributes to interactive Textual widgets to improve discoverability of commands and shortcuts, ensuring the strings are properly managed in the locale files.

## 2026-04-14 - [Use Toast Notifications for Immediate Feedback]
**Learning:** For actions like clearing the context window which happen asynchronously but don't result in immediate visual chat changes (unlike sending a message), users need explicit confirmation that the action succeeded. Textual's `notify` function provides a non-intrusive toast notification that perfectly handles this without cluttering the chat log itself.
**Action:** Always consider using `self.notify()` in Textual applications to provide immediate confirmation of successful asynchronous or background operations, ensuring the messages are localized appropriately.

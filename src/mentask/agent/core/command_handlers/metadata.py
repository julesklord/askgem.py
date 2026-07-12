from ....core.i18n import _

# Organized by category for coherence in /help
COMMAND_METADATA = {
    # --- Session & Conversation ---
    "/help": {"desc": _("cmd.desc.help"), "example": "/help", "category": "Session"},
    "/clear": {"desc": _("cmd.desc.clear"), "example": "/clear", "category": "Session"},
    "/compact": {"desc": "Compress conversation history to save tokens", "example": "/compact", "category": "Session"},
    "/reset": {"desc": "Resets the session and counters", "example": "/reset", "category": "Session"},
    "/undo": {"desc": "Restore last backed-up version of a file", "example": "/undo <path>", "category": "Session"},
    # --- History Management ---
    "/sessions": {"desc": "List previous chat sessions", "category": "History"},
    "/load": {"desc": "Load a specific session by ID or index", "example": "/load <id>", "category": "History"},
    # --- Configuration & Discovery ---
    "/model": {
        "desc": "List models or switch (use '/model configure' to test health)",
        "example": "/model [name]",
        "category": "Config",
    },
    "/discover": {"desc": "Search models.dev catalog", "example": "/discover [query]", "category": "Config"},
    "/mode": {
        "desc": "Toggle between auto/manual tool execution",
        "example": "/mode auto/manual",
        "category": "Config",
    },
    "/stream": {
        "desc": "Change streaming mode (continuous/transient)",
        "example": "/stream [mode]",
        "category": "Config",
    },
    "/colorscheme": {"desc": "List or change UI color schemes", "example": "/colorscheme [name]", "category": "Config"},
    "/thinking": {
        "desc": "Toggle visibility of agent's thought process",
        "example": "/thinking [true|false]",
        "category": "Config",
    },
    "/multiline": {"desc": "Toggle multiline prompt mode", "example": "/multiline [true|false]", "category": "Config"},
    "/init": {"desc": "Initialize local project configuration directory", "example": "/init", "category": "Config"},
    "/theme": {"desc": "Customize prompt style and icons", "example": "/theme --style atomic", "category": "Config"},
    # --- Dev Tools ---
    "/export": {"desc": "Export conversation to file", "example": "/export [md|html|txt|json]", "category": "Dev"},
    "/git": {"desc": "Git status, diff summary, or recent log", "example": "/git [status|diff|log]", "category": "Dev"},
    "/diff": {"desc": "Show uncommitted changes", "example": "/diff [file]", "category": "Dev"},
    "/context": {"desc": "Show context token usage and limits", "example": "/context", "category": "Dev"},
    "/retry": {"desc": "Re-send last user message", "example": "/retry", "category": "Dev"},
    "/config": {"desc": "Show current configuration settings", "example": "/config", "category": "Dev"},
    # --- Security ---
    "/auth": {"desc": "Sets API Key for a provider", "example": "/auth <key> [provider]", "category": "Security"},
    "/trust": {"desc": "Trust current directory for auto-execution", "example": "/trust", "category": "Security"},
    "/untrust": {"desc": "Remove trust from current directory", "example": "/untrust", "category": "Security"},
    "/readonly": {
        "desc": "Restrict agent to read-only operations on existing files",
        "example": "/readonly [true|false]",
        "category": "Security",
    },
    # --- Stats & Tools ---
    "/usage": {"desc": "Show historical token usage", "example": "/usage [--reset]", "category": "Stats"},
    "/stats": {"desc": "Show current session statistics", "example": "/stats", "category": "Stats"},
    "/artifacts": {"desc": "List or expand tool outputs", "example": "/artifacts [idx]", "category": "Tools"},
    # --- Control ---
    "/stop": {"desc": "Interrupts the current generation", "example": "/stop", "category": "Control"},
    "/exit": {"desc": _("cmd.desc.exit"), "example": "/exit", "category": "Control"},
}

# Mapping of aliases to primary commands
COMMAND_ALIASES = {
    "/q": "/exit",
    "/quit": "/exit",
    "/themes": "/colorscheme",
    "/art": "/artifacts",
    "/cost": "/stats",
    "/speed": "/speed",
}

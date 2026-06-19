

async def cmd_auth(agent, args: list[str]) -> str:
    """Sets the API Key securely and reinitializes the engine."""
    if not args:
        return (
            "[warning]Usage: /auth <your_api_key> [provider][/warning]\n"
            "[dim]Example: /auth AIza... google\n"
            "         /auth sk-... openai\n\n"
            "The key will be stored securely in your OS Keyring.[/dim]"
        )

    new_key = args[0].strip()
    provider_id = args[1].lower() if len(args) > 1 else agent.config.detect_provider(new_key)
    success = agent.config.save_api_key(new_key, provider=provider_id)
    if success:
        try:
            provider_obj = agent.session.provider
            from ..providers.gemini import GeminiProvider

            current_is_google = isinstance(provider_obj, GeminiProvider)
            target_is_google = provider_id == "google"
            if current_is_google != target_is_google:
                new_model = "gemini-2.0-flash" if target_is_google else "gpt-4o-mini"
                await agent.session.switch_model(new_model)
                agent.model_name = new_model
                agent.config.settings["model_name"] = new_model
                agent.config.save_settings()
                msg = f"[success]Provider switched to {provider_id.upper()}![/success]\n"
                msg += f"[info]New default model active:[/info] [bold]{new_model}[/bold]\n"
            else:
                await agent.session.setup_api()
                msg = f"[success]{provider_id.upper()} API Key updated and active![/success]\n"
            await agent.session.reset_session(agent._build_config())
            msg += f"[dim]The new key (***{new_key[-4:]}) is now active. Environment variables are now overridden.[/dim]"
            return msg
        except Exception as e:
            return f"[error]Key saved but engine reload failed: {e}[/error]"
    return "[error]Failed to save API Key to OS Keyring. Check system permissions.[/error]"


def cmd_readonly(agent, args: list[str]) -> str:
    """Toggles read-only mode for the agent."""
    if not args:
        current = agent.config.settings.get("readonly_mode", False)
        state = "ON" if current else "OFF"
        return f"[info]Read-only mode is currently [bold]{state}[/bold][/info]\n[dim]Usage: /readonly true | /readonly false[/dim]"

    val_str = args[0].lower()
    if val_str in ("true", "on", "yes", "1"):
        is_readonly = True
    elif val_str in ("false", "off", "no", "0"):
        is_readonly = False
    else:
        return "[error]Invalid argument. Use 'true' or 'false'.[/error]"

    agent.config.settings["readonly_mode"] = is_readonly
    agent.config.save_settings()
    agent._setup_system_prompt()  # Refresh prompt to include/exclude RO instructions

    state = "ON" if is_readonly else "OFF"
    return f"[success]Read-only mode turned [bold]{state}[/bold][/success]"

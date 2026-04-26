import asyncio
import logging

from mentask.agent.chat import ChatAgent
from mentask.core.config_manager import ConfigManager


def test_mcp_registration():
    from mentask.cli.console import console

    async def _test():
        config = ConfigManager(console)
        agent = ChatAgent()
        await agent.initialize_mcp()
        print(f"Tools registered: {len(agent.tools._tools)}")
        for name in agent.tools._tools:
            print(f" - {name}")
        await agent.close()

    asyncio.run(_test())


if __name__ == "__main__":
    test_mcp_registration()

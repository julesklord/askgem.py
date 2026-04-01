import sys
import os

def run_chatbot():
    """
    Main entry point for PyGemAi v2.0.
    """
    from .ui.console import console
    
    console.print("\n[bold cyan]PyGemAi v2.0-dev1[/bold cyan] - [dim]Initializing agentic environment...[/dim]\n")
    
    # Initialize the core chat engine
    from .engine.query_engine import QueryEngine
    engine = QueryEngine()
    engine.start()

if __name__ == "__main__":
    # Adjust python path for direct file execution execution
    if __package__ is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_chatbot()

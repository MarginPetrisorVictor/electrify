import sys
import os
import typer
from rich.console import Console
from rich.markdown import Markdown

# Ensure imports work when running from the CLI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.manager import MemoryManager
from core.orchestrator import OrchestratorAgent
from execution.dispatcher import Dispatcher

app = typer.Typer(help="Electrify AI Workflow Orchestrator")
memory = MemoryManager()
console = Console()

@app.command()
def start():
    typer.secho("⚡ Welcome to Electrify Orchestrator ⚡", fg=typer.colors.BRIGHT_BLUE, bold=True)
    
    try:
        sessions = memory.get_all_sessions()
    except Exception as e:
        typer.secho(f"Failed to connect to MongoDB: {e}", fg=typer.colors.RED)
        typer.secho("Ensure MongoDB is running locally on port 27017 or set MONGO_URI.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    
    session_id = None
    
    # Prompt the user to resume a session or start a new one
    if sessions:
        typer.secho("\n📋 Existing Sessions:", fg=typer.colors.CYAN)
        for idx, s in enumerate(sessions):
            # Display up to 5 of the most recent sessions
            if idx >= 5:
                break
            # Format datetime for better readability
            date_str = s['updated_at'].strftime("%Y-%m-%d %H:%M")
            typer.echo(f"  [{idx}] {s['name']} (Last updated: {date_str})")
            
        choice = typer.prompt("\nSelect a session number to resume, or type 'n' for a new session", default="n")
        
        if choice.lower() != 'n' and choice.isdigit() and int(choice) < len(sessions):
            session_id = str(sessions[int(choice)]['_id'])
            typer.secho(f"✅ Resuming session: {sessions[int(choice)]['name']}", fg=typer.colors.GREEN)
    
    # Create new session if requested or if no sessions exist
    if not session_id:
        name = typer.prompt("Enter a name for the new session")
        session_id = memory.create_session(name)
        typer.secho(f"✅ Created new session: {name}", fg=typer.colors.GREEN)

    # Boot up the orchestrator
    orchestrator = OrchestratorAgent()

    # REPL Loop
    while True:
        try:
            user_input = typer.prompt("\n(electrify) You", type=str)
            
            if user_input.lower() in ['exit', '/quit']:
                typer.secho("Goodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
                break
            
            # 1. Fetch recent history (last 10 turns)
            session_data = memory.get_session(session_id)
            history = session_data.get("history", [])[-10:] if session_data else []
            
            # 2. Save user query to memory
            memory.save_to_session(session_id, role="user", content=user_input)
            
            # 3. Call Orchestrator
            decision = orchestrator.decide(user_input, history)
            
            # 4. Print the conversation reply
            typer.secho("\n[Electrify]", fg=typer.colors.BRIGHT_BLUE, bold=True)
            console.print(Markdown(decision.message))
            
            artifacts = {}
            # 5. Run dispatcher if a workflow was requested
            if decision.action != "chat":
                artifacts = Dispatcher.run(decision)
            
            # 6. Save assistant response and artifacts to memory
            memory.save_to_session(session_id, role="assistant", content=decision.message, workflow_results=artifacts)
            
        except typer.Abort:
            typer.secho("\nGoodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
            break

if __name__ == "__main__":
    app()

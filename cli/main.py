import sys
import os
import typer
from rich.console import Console
from rich.markdown import Markdown
from datetime import datetime  # Fixed the import so session naming works!
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.manager import MemoryManager

app = typer.Typer(help="Electrify AI Workflow Orchestrator")
memory = MemoryManager()

@app.callback(invoke_without_command=True)
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
        # Changed \\n to \n
        typer.secho("\n📋 Existing Sessions:", fg=typer.colors.CYAN)
        for idx, s in enumerate(sessions):
            if idx >= 5:
                break
            date_str = s['updated_at'].strftime("%Y-%m-%d %H:%M")
            typer.echo(f"  [{idx}] {s['name']} (Last updated: {date_str}) - ID: {s['_id']}")
        
        # Changed \\n to \n
        choice = typer.prompt("\nChoose a session number to resume, or press Enter to create a new one", default="", show_default=False)
        if choice.isdigit() and int(choice) < len(sessions):
            selected_session = sessions[int(choice)]
            session_id = str(selected_session['_id'])
            typer.secho(f"Resuming session: {selected_session['name']}", fg=typer.colors.GREEN)
            
    if not session_id:
        session_name = typer.prompt("Enter a name for the new session", default=f"Session_{datetime.utcnow().strftime('%Y%m%d_%H%M%M')}")
        session_id = memory.create_session(session_name)
        typer.secho(f"Created new session: {session_name}", fg=typer.colors.GREEN)

    orchestrator = OrchestratorAgent()

    # REPL Loop
    while True:
        try:
            # Changed \\n to \n
            user_input = typer.prompt("\n(electrify) You", type=str)
            
            if user_input.lower() in ['exit', '/quit']:
                # Changed \\n to \n
                typer.secho("\nGoodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
                break
            
            # Fetch recent history (last 10 turns)
            session_data = memory.get_session(session_id)
            history = session_data.get("history", [])[-10:] if session_data else []
            
            # Save user query to memory
            memory.save_to_session(session_id, role="user", content=user_input)
            
            # Call Orchestrator
            decision = orchestrator.decide(user_input, history)
            
            # Print the conversation reply
            # Changed \\n to \n
            typer.secho("\n[Electrify]", fg=typer.colors.BRIGHT_BLUE, bold=True)
            console.print(Markdown(decision.message))
            
            artifacts = {}
            # Run dispatcher if a workflow was requested
            if decision.action != "chat":
                artifacts = Dispatcher.run(decision)
            
            # Save assistant response and artifacts to memory
            memory.save_to_session(session_id, role="assistant", content=decision.message, workflow_results=artifacts)
            
        except typer.Abort:
            # Changed \\n to \n
            typer.secho("\nGoodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
            break

if __name__ == "__main__":
    app()
import sys
import os
import typer
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from memory.manager import MemoryManager
from core.orchestrator import OrchestratorAgent
from execution.dispatcher import Dispatcher

app = typer.Typer(help="Electrify AI Workflow Orchestrator")
memory = MemoryManager()
console = Console()

def display_welcome():
    logo = Text("⚡", style="bold yellow")
    title = Text(" ELECTRIFY AI ", style="bold bright_blue")
    
    # Credentials section
    creds_text = Text()
    creds_text.append("Credentials: ", style="bold")
    creds_text.append(f"{os.getenv('USER', 'Guest')}", style="italic green")
    
    welcome_panel = Panel(
        Text.assemble(logo, title, "\n\n", creds_text),
        title="Welcome",
        subtitle="AI Workflow Orchestrator",
        border_style="bright_blue"
    )
    console.print(welcome_panel)

@app.callback(invoke_without_command=True)
def start():
    display_welcome()
    
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
            if idx >= 5:
                break
            date_str = s['updated_at'].strftime("%Y-%m-%d %H:%M")
            typer.echo(f"  [{idx}] {s['name']} (Last updated: {date_str}) - ID: {s['_id']}")
        
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
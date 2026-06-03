import sys
import os
import typer

# Ensure imports work when running from the CLI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.manager import MemoryManager

app = typer.Typer(help="Electrify AI Workflow Orchestrator")
memory = MemoryManager()

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

    # REPL Loop
    while True:
        try:
            user_input = typer.prompt("\n(electrify) You", type=str)
            
            if user_input.lower() in ['exit', 'quit', '/quit']:
                typer.secho("Goodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
                break
            
            # 1. Save user query to memory
            memory.save_to_session(session_id, role="user", content=user_input)
            
            # 2. Orchestrator Logic (Placeholder for Phase 2 & 3)
            typer.secho("\n[System] Orchestrating workflows... (Under Construction)", fg=typer.colors.YELLOW)
            
            response_content = "This is a placeholder response. In Phase 2, the Orchestrator LLM will parse your request and run parallel workflows here."
            typer.secho(f"[Assistant] {response_content}", fg=typer.colors.GREEN)
            
            # 3. Save assistant response to memory
            memory.save_to_session(session_id, role="assistant", content=response_content)
            
        except typer.Abort:
            typer.secho("\nGoodbye! ⚡", fg=typer.colors.BRIGHT_BLUE)
            break

if __name__ == "__main__":
    app()

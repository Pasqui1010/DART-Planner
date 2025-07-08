"""
Command-line interface for managing users and the auth database.
"""
import asyncio
import typer
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command

from security.db import database, models, service
from security.auth import Role

app = typer.Typer()
user_service = service.UserService()

def get_db_session():
    """Provides a database session for CLI commands."""
    return next(database.get_db())

@app.command()
def db_upgrade(revision: str = "head"):
    """Upgrades the database to the latest revision or a specific one."""
    typer.echo("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, revision)
    typer.echo("Database migration complete.")

@app.command()
def create_admin(
    username: str = typer.Option(..., "--username", "-u", help="Admin username"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password"),
):
    """Creates a new admin user."""
    db = get_db_session()
    async def _create_admin():
        existing_user = await user_service.get_user_by_username(db, username)
        if existing_user:
            typer.echo(f"Error: User '{username}' already exists.")
            raise typer.Exit(code=1)
        
        user = await user_service.create_user(db, username=username, password=password, role=Role.ADMIN)
        typer.echo(f"Admin user '{user.username}' created successfully.")

    asyncio.run(_create_admin())
    db.close()

@app.command()
def create_user(
    username: str = typer.Option(..., "--username", "-u", help="Username"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="User password"),
    role: Role = typer.Option(Role.OPERATOR, "--role", "-r", help="User role"),
):
    """Creates a standard user."""
    db = get_db_session()
    async def _create_user():
        existing_user = await user_service.get_user_by_username(db, username)
        if existing_user:
            typer.echo(f"Error: User '{username}' already exists.")
            raise typer.Exit(code=1)
            
        user = await user_service.create_user(db, username=username, password=password, role=role)
        typer.echo(f"User '{user.username}' with role '{user.role.value}' created successfully.")
    
    asyncio.run(_create_user())
    db.close()

@app.command()
def list_users():
    """Lists all users in the database."""
    db = get_db_session()
    async def _list_users():
        users = await user_service.get_all_users(db)
        if not users:
            typer.echo("No users found.")
            return
        
        typer.echo("Users:")
        for user in users:
            typer.echo(f"  - ID: {user.id}, Username: {user.username}, Role: {user.role.value}, Active: {user.is_active}")
            
    asyncio.run(_list_users())
    db.close()

@app.command()
def delete_user(username: str = typer.Option(..., "--username", "-u", help="The username of the user to delete.")):
    """Deletes a user."""
    db = get_db_session()
    async def _delete_user():
        user = await user_service.get_user_by_username(db, username)
        if not user:
            typer.echo(f"Error: User '{username}' not found.")
            raise typer.Exit(code=1)
        
        await user_service.delete_user(db, user.id)
        typer.echo(f"User '{username}' deleted successfully.")

    asyncio.run(_delete_user())
    db.close()


if __name__ == "__main__":
    app() 

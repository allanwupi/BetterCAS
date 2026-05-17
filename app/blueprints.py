from flask import Blueprint

main = Blueprint('main', __name__)

from app import db, models, routes

@main.cli.command('init-db')
def init_db_command():
    """Create database tables for local development."""
    db.create_all()
    print('Database tables created.')


@main.cli.command('clear-db')
def clear_db_command():
    """Clear all data from the database tables for local development."""
    db.drop_all()
    db.create_all()
    print('Database tables cleared and recreated.')
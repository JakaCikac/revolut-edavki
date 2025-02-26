"""Command line interface for revolut-edavki."""

import os
import sys
import click
from dotenv import load_dotenv
from .app import app

@click.command()
@click.option('--port', '-p', default=59855, help='Port to run the server on')
@click.option('--host', '-h', default='127.0.0.1', help='Host to bind to')
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to config file')
def main(port, host, debug, config):
    """Start the revolut-edavki web application."""
    # Load environment variables
    if config:
        load_dotenv(config)
    else:
        # Try to load from current directory or package directory
        local_env = os.path.join(os.getcwd(), '.env')
        package_env = os.path.join(os.path.dirname(__file__), '.env')
        
        if os.path.exists(local_env):
            load_dotenv(local_env)
        elif os.path.exists(package_env):
            load_dotenv(package_env)
    
    # Check required environment variables
    if not os.getenv('TAX_SALT'):
        click.echo("Error: TAX_SALT environment variable is required", err=True)
        sys.exit(1)
    
    # Start the application
    click.echo(f"Starting revolut-edavki on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
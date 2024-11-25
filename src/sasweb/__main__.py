import click
from nicegui import ui, app
from index import index

@click.command()
@click.option('--host', default='127.0.0.1', help='Host address to bind to')
@click.option('--port', default=8080, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def main(host, port, debug):
    """Launch the SASWEB application."""
    ui.run(
        host=host,
        port=port,
        storage_secret='sasweb-secret',
        reload=debug,
        show=False,  # Don't automatically open browser
    )

if __name__ == '__main__':
    main()

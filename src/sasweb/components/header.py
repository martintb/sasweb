from nicegui import ui

def create_header(title='SASWEB'):
    """Creates a consistent header for all pages"""
    with ui.header().classes('w-full flex justify-between items-center p-4 bg-blue-600 text-white'):
        with ui.row():
            #ui.image('header.png')
            ui.label(title).classes('text-h6 ml-4')
            #ui.link('Home', '/').classes('text-white mx-2')

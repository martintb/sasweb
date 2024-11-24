'''
https://github.com/zauberzeug/nicegui/blob/249810f7ed6e755a5a2da206c5f8f33d9c2a6dd0/examples/modularization/theme.py
'''
from contextlib import contextmanager

from menu import menu

from nicegui import ui


@contextmanager
def frame(navtitle: str):
    """Custom page frame to share the same styling and behavior across all pages"""
    ui.colors(primary='#6E93D6', secondary='#53B689', accent='#111B1E', positive='#53B689')
    with ui.header().classes('justify-between text-white'):
        ui.label('Modularization Example').classes('font-bold')
        ui.label(navtitle)
        with ui.row():
            menu()
    with ui.column().classes('absolute-center items-center'):
        yield''
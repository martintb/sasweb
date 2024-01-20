import os
import tempfile
import uuid

import plotly.graph_objects as go

from nicegui import events, ui, app
from sasdata.dataloader.loader import Loader

from FitPage1D import FitPage1D

@ui.page('/')
def index():
    # initialize global holding file table state
    app.storage.user['FILE_METADATA'] = []
    app.storage.user['FILE_DATA_1D'] = {}
    FILE_DATA = {}

    def handle_upload(e: events.UploadEventArguments):
        filename = e.name
        uid = str(uuid.uuid4())
        app.storage.user['FILE_METADATA'].append({'filename': filename, 'label': filename, 'uuid': uid})
        file_table.update()

        FILE_DATA.update({uid: e.content})

    async def plot_selected():
        selected_rows = await file_table.get_selected_rows()

        plotly_fig.data = []  #clear plotly
        for row in selected_rows:
            uid = row['uuid']
            filename = row['filename']
            ext = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(mode='wb', delete=True, suffix=ext) as tf:
                file_data = FILE_DATA[uid]
                file_data.seek(0)
                tf.write(file_data.read())
                for data in Loader().load(tf.name):
                    plotly_fig.add_trace(go.Scatter(x=data.x, y=data.y,
                                                    mode='markers',
                                                    name=row['label']))
        ng_fig.update()

    async def send_to_fit():
        selected_rows = await file_table.get_selected_rows()

        for row in selected_rows:
            uid = row['uuid']

        for row in selected_rows:
            uid = row['uuid']
            filename = row['filename']
            label = row['label']
            ext = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(mode='wb', delete=True, suffix=ext) as tf:
                file_data = FILE_DATA[uid]
                file_data.seek(0)
                tf.write(file_data.read())
                for data in Loader().load(tf.name):
                    app.storage.user['FILE_DATA_1D'].update({
                        uid: {
                            'x':data.x,
                            'y': data.y,
                            'dx': data.dx,
                            'dy': data.dy,
                            'filename':filename,
                            'label': label,
                        }
                    })
            ui.open(f'/FitPage1D/{uid}',new_tab=True)


    with ui.row().classes('w-full justify-center'):
        with ui.card().classes('w-1/2 no-wrap'):
            with ui.row().classes('w-full no-wrap'):
                upload = ui.upload(label="Upload Data",on_upload=handle_upload, multiple=True, auto_upload=True)
                upload.classes('w-1/2 float-left')

                with ui.column().classes('w-full no-wrap'):
                    file_table = ui.aggrid({
                        "columnDefs": [
                            {"field": "filename", "editable": False, "sortable": True, "filter": "agTextColumnFilter",
                             "floatingFilter": True, 'checkboxSelection': True},
                            {"field": "label", "editable": True},
                            {"field": "uuid", 'hide': True},
                        ],
                        "rowData": app.storage.user['FILE_METADATA'],
                        "rowSelection": "multiple",
                        "stopEditingWhenCellsLoseFocus": True,
                    })
                    file_table.classes('w-full float-left')

                    plot_button = ui.button(text='Quickplot Selected', on_click=plot_selected).classes('float-right')
                    plot_button.classes('w-full float-left')

                    plot_button = ui.button(text='Send Selected to Fitpage', on_click=send_to_fit,color='green').classes('float-right')
                    plot_button.classes('w-full float-left')


            plotly_fig = go.Figure()
            plotly_fig.update_xaxes(title='q', type='log')
            plotly_fig.update_yaxes(title='Intensity', type='log')
            ng_fig = ui.plotly(plotly_fig).classes('w-full')
        #with ui.row().classes('w-full justify-center'):
        #with ui.card().classes('w-1/2'):
        #    ng_fig = ui.plotly(plotly_fig).classes('w-full')

ui.run(storage_secret='secret')

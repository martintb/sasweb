from nicegui import app, ui, events

import plotly.graph_objects as go

import sasmodels.core
import sasmodels.data
import sasmodels.direct_model

from collections import defaultdict
import numpy as np
from nicegui.elements.aggrid import AgGrid

# For development only, remove for production
from sasdata.dataloader.loader import Loader


# End development only

# @ui.page('/FitPage1D/{uid}')
# def FitPage1D(uid:str):
#     ui.label('FitPage1D')


# >> For development only, remove for production
@ui.page('/')
def FitPage1D():
    uid = 123
    sasdata = Loader().load('/Users/tbm/projects/1910-Toyota/2020-02-04-KSM-Inks/reduced/Nafion Ink CIL 0.5D.ABS')
    app.storage.user['FILE_DATA_1D'] = {}
    app.storage.user['FILE_DATA_1D'][uid] = {}
    app.storage.user['FILE_DATA_1D'][uid]['x'] = sasdata[0].x
    app.storage.user['FILE_DATA_1D'][uid]['y'] = sasdata[0].y
    app.storage.user['FILE_DATA_1D'][uid]['dx'] = sasdata[0].dx
    app.storage.user['FILE_DATA_1D'][uid]['dy'] = sasdata[0].dy
    app.storage.user['FILE_DATA_1D'][uid]['label'] = 'Nafion Ink CIL 0.5D.ABS'

    app.storage.user['FIT_DATA_1D'] = {}
    # >> End development only

    app.storage.user['FIT_DATA_1D'][uid] = {'parameters': []}
    LOCAL_DATA = {}  # need somehwere to store non-serliazable data

    plotly_fig = go.Figure()
    plotly_fig.update_xaxes(title='q', type='log')
    plotly_fig.update_yaxes(title='Intensity', type='log')

    plotly_fig.add_trace(
        go.Scatter(
            x=app.storage.user['FILE_DATA_1D'][uid]['x'],
            y=app.storage.user['FILE_DATA_1D'][uid]['y'],
            mode='markers',
            name=app.storage.user['FILE_DATA_1D'][uid]['label'],
        ))

    def select_model(e):
        app.storage.user['FIT_DATA_1D'][uid]['model'] = e.value

        Data1D = sasmodels.data.Data1D(
            x=app.storage.user['FILE_DATA_1D'][uid]['x'],
            y=app.storage.user['FILE_DATA_1D'][uid]['y'],
            dx=app.storage.user['FILE_DATA_1D'][uid]['dx'],
            dy=app.storage.user['FILE_DATA_1D'][uid]['dy'],
        )

        kernel = sasmodels.core.load_model(e.value)
        del app.storage.user['FIT_DATA_1D'][uid]['parameters'][:]
        for name, value in kernel.info.parameters.defaults.items():
            parameter = {}
            parameter['name'] = name
            parameter['value'] = value
            parameter['min'] = -np.inf
            parameter['max'] = np.inf
            parameter['unit'] = ''
            app.storage.user['FIT_DATA_1D'][uid]['parameters'].append(parameter)

        LOCAL_DATA['Data1D'] = Data1D
        LOCAL_DATA['calculator'] = sasmodels.direct_model.DirectModel(data=Data1D, model=kernel)
        update_model(None)
        parameter_table.update()

    def update_model(event):
        if len(plotly_fig.data) > 1:
            plotly_fig.data = plotly_fig.data[:1]

        if event is not None:
            kwargs = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}
            kwargs.update({event.args['data']['name']: event.args['data']['value']})
        else:
            kwargs = {}

        plotly_fig.add_trace(
            go.Scatter(
                x=LOCAL_DATA['Data1D'].x,
                y=LOCAL_DATA['calculator'](**kwargs),
                mode='markers',
                name=app.storage.user['FIT_DATA_1D'][uid]['model']
            )
        )
        ng_fig.update()

    with ui.row().classes('w-full justify-center'):
        with ui.card().classes('w-1/2'):
            ui.label('FitPage1D')

            ng_fig = ui.plotly(plotly_fig)
            ng_fig.classes('w-full')

            with ui.row().classes('w-full float-left'):
                ui.select(
                    label="Model",
                    options=sasmodels.core.list_models(),
                    with_input=True,
                    on_change=select_model,
                ).classes('w-1/3 float-left')

                ui.button('Fit').classes('w-1/3 float-left')

            parameter_table = ui.aggrid({
                "columnDefs": [
                    {"field": "name", 'checkboxSelection': True, 'hide': False},
                    {"field": "value", "editable": True},
                    {"field": "min", "editable": True},
                    {"field": "max", "editable": True},
                    {"field": "units", "editable": False},
                ],
                "rowData": app.storage.user['FIT_DATA_1D'][uid]['parameters'],
                "rowSelection": "multiple",
                "stopEditingWhenCellsLoseFocus": True,
            })
            parameter_table.on('cellValueChanged', update_model)


# >> For development only, remove for production
ui.run(storage_secret='secret')
# >> End development only

import plotly.graph_objects as go
import sasmodels.core
import sasmodels.data
import sasmodels.direct_model
import sasmodels.bumps_model
from nicegui import app, ui

from collections import namedtuple

# For development only, remove for production
from sasdata.dataloader.loader import Loader
import bumps
import bumps.fitproblem
import bumps.fitters

DEBUG_MODE = False

# End development only

@ui.page('/FitPage1D/{uid}')
def FitPage1D(uid:str):

# >> For development only, remove for production
# @ui.page('/')
# def FitPage1D():
    if DEBUG_MODE:
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

    LOCAL_DATA = {}  # need somewhere to store non-serializable data
    if uid not in app.storage.user['FIT_DATA_1D']:
        app.storage.user['FIT_DATA_1D'][uid] = {}
        app.storage.user['FIT_DATA_1D'][uid]['parameters'] = []


    def select_model(e):
        app.storage.user['FIT_DATA_1D'][uid]['model'] = e.value

        LOCAL_DATA['data'] = sasmodels.data.Data1D(
            x=app.storage.user['FILE_DATA_1D'][uid]['x'],
            y=app.storage.user['FILE_DATA_1D'][uid]['y'],
            dx=app.storage.user['FILE_DATA_1D'][uid]['dx'],
            dy=app.storage.user['FILE_DATA_1D'][uid]['dy'],
        )

        LOCAL_DATA['kernel'] = sasmodels.core.load_model(e.value)
        del app.storage.user['FIT_DATA_1D'][uid]['parameters'][:]
        for name, value in LOCAL_DATA['kernel'].info.parameters.defaults.items():
            parameter = {}
            parameter['name'] = name
            parameter['value'] = value
            parameter['min'] = '-np.inf'
            parameter['max'] = '+np.inf'
            parameter['unit'] = ''
            app.storage.user['FIT_DATA_1D'][uid]['parameters'].append(parameter)

        LOCAL_DATA['calculator'] = sasmodels.direct_model.DirectModel(
            data=LOCAL_DATA['data'],
            model=LOCAL_DATA['kernel']
        )
        parameter_table.update()
        update_plot(None)

    def update_plot(event):
        if len(plotly_fig.data) > 1:
            plotly_fig.data = plotly_fig.data[:1]

        if event is not None:
            value = event.args['data']['value']
            rowIndex = event.args['rowIndex']
            app.storage.user['FIT_DATA_1D'][uid]['parameters'][rowIndex]['value'] = value
            kwargs = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}

        kwargs = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}

        print(kwargs)
        plotly_fig.add_trace(
            go.Scatter(
                x=LOCAL_DATA['data'].x,
                y=LOCAL_DATA['calculator'](**kwargs),
                mode='markers',
                name=app.storage.user['FIT_DATA_1D'][uid]['model']
            )
        )
        ng_fig.update()

    async def fit_model(event):
        if 'kernel' not in LOCAL_DATA:
            with ui.dialog() as dialog, ui.card():
                ui.label('Error: No model selected.')
                ui.button('Close', on_click=dialog.close)
            dialog.open()
            return

        params = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}
        LOCAL_DATA['bumps_model'] = sasmodels.bumps_model.Model(LOCAL_DATA['kernel'], **params)

        selected_rows = await parameter_table.get_selected_rows()
        if not selected_rows:
            with ui.dialog() as dialog, ui.card():
                ui.label('Error: No parameters selected for fit...')
                ui.button('Close', on_click=dialog.close)
            dialog.open()
            return

        for param in selected_rows:
            if 'inf' in param['min']:
                pmin = 1e-9
            else:
                pmin = float(param['min'])
            if 'inf' in param['max']:
                pmax = 1e9
            else:
                pmax = float(param['max'])
            getattr(LOCAL_DATA['bumps_model'], param['name']).range(pmin, pmax)

        LOCAL_DATA['bumps_experiment'] = sasmodels.bumps_model.Experiment(data=LOCAL_DATA['data'], model=LOCAL_DATA['bumps_model'])
        LOCAL_DATA['bumps_problem'] = bumps.fitproblem.FitProblem(LOCAL_DATA['bumps_experiment'])
        LOCAL_DATA['fit_results'] = bumps.fitters.fit(LOCAL_DATA['bumps_problem'])

        #update table
        fit_results = LOCAL_DATA['bumps_problem'].fitness.model.state()
        for param in app.storage.user['FIT_DATA_1D'][uid]['parameters']:
            param['value'] = fit_results[param['name']]
        parameter_table.update()
        update_plot(None)


    with ui.row().classes('w-full justify-center'):
        with ui.card().classes('w-1/2'):
            plotly_fig = go.Figure()
            plotly_fig.update_xaxes(title='q', type='log')
            plotly_fig.update_yaxes(title='Intensity', type='log')
            plotly_fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(yanchor="top", y=1.0, xanchor="right", x=1.0)
            )

            plotly_fig.add_trace(
                go.Scatter(
                    x=app.storage.user['FILE_DATA_1D'][uid]['x'],
                    y=app.storage.user['FILE_DATA_1D'][uid]['y'],
                    mode='markers',
                    name=app.storage.user['FILE_DATA_1D'][uid]['label'],
                ))

            ng_fig = ui.plotly(plotly_fig)
            ng_fig.classes('w-full')

            with ui.row().classes('w-full float-left'):
                ui.select(
                    label="Choose Model",
                    options=sasmodels.core.list_models(),
                    with_input=True,
                    on_change=select_model,
                ).classes('w-1/3 float-left')

                ui.button('Configure Fit').classes('w-1/4 float-left')
                ui.button('Fit',on_click=fit_model).classes('w-1/4 float-left')


            parameter_table = ui.aggrid({
                "columnDefs": [
                    {"field": "name", "editable": False, "sortable": True, "filter": "agTextColumnFilter",
                     "floatingFilter": True, 'checkboxSelection': True},
                    {"field": "value", "editable": True},
                    {"field": "min", "editable": True},
                    {"field": "max", "editable": True},
                    {"field": "units", "editable": False},
                ],
                "rowData": app.storage.user['FIT_DATA_1D'][uid]['parameters'],
                "rowSelection": "multiple",
                "stopEditingWhenCellsLoseFocus": True,
            })
            parameter_table.on('cellValueChanged', update_plot)




if DEBUG_MODE:
    # >> For development only, remove for production
    ui.run(storage_secret='secret')
    # >> End development only

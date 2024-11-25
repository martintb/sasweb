import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import sasmodels.core
import sasmodels.data
import sasmodels.direct_model
import sasmodels.bumps_model
import bumps.fitproblem
import bumps.fitters
from nicegui import app, ui
from components.header import create_header

from sasdata.dataloader.loader import Loader

# Available optimizers and their parameters
OPTIMIZER_CONFIGS = {
    'LM': {'method':'lm','steps': 100, 'ftol': 1e-6, 'xtol': 1e-6},
    'DREAM': {'method':'dream','steps': 1000, 'burn': 100, 'population': 10},
    'DE': {'method':'de','steps': 200, 'population': 10, 'crossover': 0.8, 'scale': 0.5}
}

DEBUG_MODE = True

# Constants

@ui.page('/FitPage1D/{uid}')
def FitPage1D(uid: str):

# # >> For development only, remove for production
# @ui.page('/')
# def FitPage1D():
#     if DEBUG_MODE:
#         uid = 123
#         sasdata = Loader().load('/Users/tbm/projects/1910-Toyota/2020-02-04-KSM-Inks/reduced/Nafion Ink CIL 0.5D.ABS')
#         app.storage.user['FILE_DATA_1D'] = {}
#         app.storage.user['FILE_DATA_1D'][uid] = {}
#         app.storage.user['FILE_DATA_1D'][uid]['x'] = sasdata[0].x
#         app.storage.user['FILE_DATA_1D'][uid]['y'] = sasdata[0].y
#         app.storage.user['FILE_DATA_1D'][uid]['dx'] = sasdata[0].dx
#         app.storage.user['FILE_DATA_1D'][uid]['dy'] = sasdata[0].dy
#         app.storage.user['FILE_DATA_1D'][uid]['label'] = 'Nafion Ink CIL 0.5D.ABS'
#
#         app.storage.user['FIT_DATA_1D'] = {}
#         # >> End development only

    LOCAL_DATA = {}  # need somewhere to store non-serializable data
    PARAMETER_TABLE = None
    PLOTLY_FIG = None

    # Add header
    create_header(title='SASWEB - Fit 1D - ' + app.storage.user['FILE_DATA_1D'][uid]['label'])

    if uid not in app.storage.user['FIT_DATA_1D']:
        app.storage.user['FIT_DATA_1D'][uid] = {'parameters': []}

    def initialize_plot():
        PLOTLY_FIG = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3], vertical_spacing=0.1
        )
        PLOTLY_FIG.update_xaxes(type='log',row=1,col=1)
        PLOTLY_FIG.update_xaxes(title='q', type='log',row=2,col=1)
        PLOTLY_FIG.update_yaxes(title='Intensity', type='log',row=1,col=1)
        PLOTLY_FIG.update_yaxes(title='Residual', type='linear',row=2,col=1)
        PLOTLY_FIG.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(yanchor="top", y=1.0, xanchor="right", x=1.0)
        )
        PLOTLY_FIG.add_trace(
            go.Scatter(
                x=app.storage.user['FILE_DATA_1D'][uid]['x'],
                y=app.storage.user['FILE_DATA_1D'][uid]['y'],
                mode='markers',
                name=app.storage.user['FILE_DATA_1D'][uid]['label'],
            ),
            row=1,col=1,
        )
        PLOTLY_FIG.add_trace(
            go.Scatter(
                x=app.storage.user['FILE_DATA_1D'][uid]['x'][[0,-1]],
                y=[0.0,0.0],
                mode='lines',
                line=dict(color='black', width=1, dash='dot'),
                showlegend=False,
            ),
            row=2,col=1,
        )

        PLOTLY_FIG.update_layout(
            hovermode='x unified',
        )
        return PLOTLY_FIG

    def select_model(event):
        app.storage.user['FIT_DATA_1D'][uid]['model'] = event.value
        LOCAL_DATA['data'] = sasmodels.data.Data1D(
            x=app.storage.user['FILE_DATA_1D'][uid]['x'],
            y=app.storage.user['FILE_DATA_1D'][uid]['y'],
            dx=app.storage.user['FILE_DATA_1D'][uid]['dx'],
            dy=app.storage.user['FILE_DATA_1D'][uid]['dy'],
        )
        LOCAL_DATA['kernel'] = sasmodels.core.load_model(event.value)

        # need to clear and append/extend to keep the same reference
        del app.storage.user['FIT_DATA_1D'][uid]['parameters'][:]
        app.storage.user['FIT_DATA_1D'][uid]['parameters'].extend([
            {'name': name, 'value': value, 'min': '-np.inf', 'max': '+np.inf', 'unit': ''}
            for name, value in LOCAL_DATA['kernel'].info.parameters.defaults.items()
        ])

        LOCAL_DATA['calculator'] = sasmodels.direct_model.DirectModel(
            data=LOCAL_DATA['data'],
            model=LOCAL_DATA['kernel']
        )
        PARAMETER_TABLE.update()
        update_plot(None)

    def update_plot(event):
        if len(PLOTLY_FIG.data) > 2:
            PLOTLY_FIG.data = PLOTLY_FIG.data[:2]

        if event is not None:
            value = event.args['data']['value']
            rowIndex = event.args['rowIndex']
            app.storage.user['FIT_DATA_1D'][uid]['parameters'][rowIndex]['value'] = value

        kwargs = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}

        x = LOCAL_DATA['data'].x
        y = LOCAL_DATA['data'].y
        yth = LOCAL_DATA['calculator'](**kwargs)

        if LOCAL_DATA['data'] is not None:
            dy = LOCAL_DATA['data'].dy
        else:
            dy = np.sqrt(LOCAL_DATA['data'].y)
        residual = (yth - y)/dy

        PLOTLY_FIG.add_trace(
            go.Scatter(
                x=x,
                y=yth,
                mode='markers',
                name=app.storage.user['FIT_DATA_1D'][uid]['model']
            ),
            row=1, col=1,
        )
        PLOTLY_FIG.add_trace(
            go.Scatter(
                x=x,
                y=residual,
                mode='markers',
                name='residual',
                showlegend=False,
            ),
            row=2, col=1,
        )
        ng_fig.update()

    async def fit_model(event):
        if 'kernel' not in LOCAL_DATA:
            show_error_dialog('Error: No model selected.')
            return

        params = {item['name']: item['value'] for item in app.storage.user['FIT_DATA_1D'][uid]['parameters']}
        LOCAL_DATA['bumps_model'] = sasmodels.bumps_model.Model(LOCAL_DATA['kernel'], **params)

        selected_rows = await PARAMETER_TABLE.get_selected_rows()
        if not selected_rows:
            show_error_dialog('Error: No parameters selected for fit...')
            return

        for param in selected_rows:
            pmin = 1e-9 if 'inf' in param['min'] else float(param['min'])
            pmax = 1e9 if 'inf' in param['max'] else float(param['max'])
            getattr(LOCAL_DATA['bumps_model'], param['name']).range(pmin, pmax)

        LOCAL_DATA['bumps_experiment'] = sasmodels.bumps_model.Experiment(data=LOCAL_DATA['data'], model=LOCAL_DATA['bumps_model'])
        LOCAL_DATA['bumps_problem'] = bumps.fitproblem.FitProblem(LOCAL_DATA['bumps_experiment'])
        
        # Use configured optimizer
        optimizer = app.storage.user.get('optimizer', {'type': 'LM', 'params': OPTIMIZER_CONFIGS['LM']})
        LOCAL_DATA['fit_results'] = bumps.fitters.fit(
            LOCAL_DATA['bumps_problem'],
            **optimizer['params']
        )

        fit_results = LOCAL_DATA['bumps_problem'].fitness.model.state()
        for param in app.storage.user['FIT_DATA_1D'][uid]['parameters']:
            param['value'] = fit_results[param['name']]
        PARAMETER_TABLE.update()
        update_plot(None)

    def show_error_dialog(message):
        with ui.dialog() as dialog, ui.card():
            ui.label(message)
            ui.button('Close', on_click=dialog.close)
        dialog.open()

    async def copy_parameters():
        """Copy current parameters to clipboard"""
        try:
            params = app.storage.user['FIT_DATA_1D'][uid]['parameters']
            # Convert np.inf to string representation for JSON serialization
            params_copy = []
            for param in params:
                param_copy = param.copy()
                param_copy['min'] = str(param_copy['min'])
                param_copy['max'] = str(param_copy['max'])
                param_copy = {k: (v if v is not None else 'None') for k, v in param_copy.items()}
                params_copy.append(param_copy)

            json_str = json.dumps(params_copy)
            #await ui.run_javascript(f'navigator.clipboard.writeText({json_str})')
            ui.clipboard.write(json_str)
            ui.notify('Parameters copied to clipboard', type='positive')
        except Exception as e:
            show_error_dialog(f'Error copying parameters: {str(e)}')

    async def paste_parameters():
        """Paste parameters from clipboard"""
        try:
            clipboard_text = await ui.clipboard.read()

            # Parse and validate the JSON data
            params = json.loads(clipboard_text)

            # Validate structure
            required_keys = {'name', 'value', 'min', 'max', 'unit'}
            if not all(isinstance(p, dict) and required_keys.issubset(p.keys()) for p in params):
                raise ValueError("Invalid parameter format")

            # Update parameters
            current_params = app.storage.user['FIT_DATA_1D'][uid]['parameters']
            param_names = {p['name'] for p in current_params}

            # Only update existing parameters
            for new_param in params:
                if new_param['name'] in param_names:
                    for curr_param in current_params:
                        if curr_param['name'] == new_param['name']:
                            curr_param.update(new_param)

            PARAMETER_TABLE.update()
            update_plot(None)
            ui.notify('Parameters pasted successfully', type='positive')
        except json.JSONDecodeError:
            show_error_dialog('Invalid clipboard content: Not valid JSON')
        except Exception as e:
            show_error_dialog(f'Error pasting parameters: {str(e)}')

    def show_config_dialog():
        with ui.dialog() as dialog, ui.card():
            ui.label('Optimizer Configuration').classes('text-h6 mb-4')

            # Initialize optimizer settings if they don't exist
            if 'optimizer' not in app.storage.user:
                app.storage.user['optimizer'] = {
                    'type': 'LM',
                    'params': OPTIMIZER_CONFIGS['LM'].copy()
                }

            def update_optimizer_params(evt):
                selected = evt.value
                app.storage.user['optimizer']['type'] = selected
                app.storage.user['optimizer']['params'] = OPTIMIZER_CONFIGS[selected].copy()
                # Clear and recreate parameter inputs
                params_container.clear()
                create_parameter_inputs(params_container)
            
            def create_parameter_inputs(container):
                with container:
                    for param, value in app.storage.user['optimizer']['params'].items():
                        if param == 'method':
                            continue
                        elif type(value) == str:
                            ui.input(
                                label=param,
                                value=value,
                                on_change=lambda e, p=param: setattr(
                                    app.storage.user['optimizer']['params'],
                                    p,
                                    e.value
                                )
                            )
                        else:
                            ui.number(
                                label=param,
                                value=value,
                                on_change=lambda e, p=param: setattr(
                                    app.storage.user['optimizer']['params'],
                                    p,
                                    e.value
                                )
                            )

            # Optimizer selection dropdown
            ui.select(
                label='Optimizer',
                options=list(OPTIMIZER_CONFIGS.keys()),
                value=app.storage.user['optimizer']['type'],
                on_change=update_optimizer_params
            ).classes('w-full mb-4')

            # Container for parameter inputs
            params_container = ui.column().classes('w-full')
            create_parameter_inputs(params_container)
            
            # Close button
            ui.button('Close', on_click=dialog.close).classes('mt-4')
        dialog.open()

    PLOTLY_FIG = initialize_plot()

    with ui.column().classes('w-full max-w-[1600px] mx-auto p-4'):
        # Top row for controls
        with ui.row().classes('w-full max-w-[600px] gap-4 mb-4'):
            ui.select(
                label="Choose Model",
                options=sasmodels.core.list_models(),
                with_input=True,
                on_change=select_model,
            ).classes('flex-grow')
        with ui.row().classes('w-full max-w-[600px] gap-4 mb-4'):
            ui.button('Fit', on_click=fit_model).classes('self-end')
            ui.button('Copy', on_click=copy_parameters).classes('self-end')
            ui.button('Paste', on_click=paste_parameters).classes('self-end')
            ui.button('Configure', on_click=show_config_dialog).classes('self-end')

        # Main content row
        with ui.row().classes('w-full gap-4 flex-wrap lg:flex-nowrap'):
            # Left column - Parameter Table
            with ui.card().classes('flex-grow-0 w-full min-w-[600px] max-w-[800px]'):
                PARAMETER_TABLE = ui.aggrid({
                    "columnDefs": [
                        {"field": "name", "editable": False, "sortable": True, 
                         "filter": "agTextColumnFilter", "floatingFilter": True, 
                         'checkboxSelection': True},
                        {"field": "value", "editable": True},
                        {"field": "min", "editable": True},
                        {"field": "max", "editable": True},
                        {"field": "units", "editable": False},
                    ],
                    "rowData": app.storage.user['FIT_DATA_1D'][uid]['parameters'],
                    "rowSelection": "multiple",
                    "stopEditingWhenCellsLoseFocus": True,
                })
                PARAMETER_TABLE.on('cellValueChanged', update_plot)

            # Right column - Plot
            with ui.card().classes('flex-grow min-w-[500px] max-w-[800px]'):
                ng_fig = ui.plotly(PLOTLY_FIG).classes('w-full')

if DEBUG_MODE:
    # For development only, remove for production
    ui.run(storage_secret='secret')

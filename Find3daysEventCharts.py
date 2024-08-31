import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, Input, Output

# Connect to the SQLite database
db_path = 'data/IntradayGGData.db'  # Replace with the path to your database file
conn = sqlite3.connect(db_path)

# Load the data from the BankNifty table
banknifty_data = pd.read_sql_query("SELECT * FROM banknifty;", conn)

# Convert the datetime column to datetime if it's not already
banknifty_data['datetime'] = pd.to_datetime(banknifty_data['datetime'])

# Extract just the date part for grouping
banknifty_data['date'] = banknifty_data['datetime'].dt.date
banknifty_data['date'] = pd.to_datetime(banknifty_data['date'])

# Filter for dates greater than 31-12-2020
banknifty_data = banknifty_data[banknifty_data['date'] > pd.to_datetime('2020-12-31')]

# Group data by date and calculate the daily high and low
daily_range = banknifty_data.groupby('date').agg(
    daily_high=('high', 'max'),
    daily_low=('low', 'min')
).reset_index()

# Calculate the daily range
daily_range['range'] = daily_range['daily_high'] - daily_range['daily_low']

# Filter days with a one-sided move of 500 points or more
one_sided_days = daily_range[daily_range['range'] >= 500].copy()

# Function to identify V-shaped movements
def identify_v_shaped_movement(df):
    df['open_close_diff'] = df['close'] - df['open']
    df['intraday_high_low_diff'] = df['high'] - df['low']

    v_shaped_days = df[
        ((df['open_close_diff'] > 0) & ((df['open'] - df['low']) >= 250) & ((df['high'] - df['close']) <= 50)) |
        ((df['open_close_diff'] < 0) & ((df['high'] - df['open']) >= 250) & ((df['close'] - df['low']) <= 50))
        ].copy()

    return v_shaped_days

# Apply this logic to the BankNifty data to find V-shaped days
v_shaped_days = identify_v_shaped_movement(banknifty_data)

# Combine one-sided and V-shaped moves
significant_days = pd.concat([one_sided_days, v_shaped_days], ignore_index=True).drop_duplicates()

# Function to find the nearest previous or next trading day
def find_nearest_day(df, target_date, direction='previous'):
    if direction == 'previous':
        return df[df['date'] < target_date]['date'].max()
    elif direction == 'next':
        return df[df['date'] > target_date]['date'].min()

# Add previous and next days
significant_days['previous_day'] = significant_days['date'].apply(
    lambda x: find_nearest_day(daily_range, x, 'previous'))
significant_days['next_day'] = significant_days['date'].apply(lambda x: find_nearest_day(daily_range, x, 'next'))

# Calculate the AD Line (weighted) and its EMA, along with weighted volume
# Assuming 'adline' and 'volume' columns exist in the banknifty_data DataFrame
#banknifty_data['ad_lineweighted'] = banknifty_data['AD_line']  # Use your logic for weighted AD Line
banknifty_data['ema_9'] = banknifty_data['AD_LineWeighted'].ewm(span=9, adjust=False).mean()
#banknifty_data['weighted_volume'] = banknifty_data['volume']  # Use your logic for weighted volume

# Determine whether the close is higher or lower than the previous close
banknifty_data['volume_color'] = ['green' if banknifty_data['close'].iloc[i] >= banknifty_data['close'].iloc[i-1] else 'red'
                                  for i in range(len(banknifty_data))]

def GetMissingDatesInRange(fromdate ,todate,existing_dates):
    # Define the start and end dates
    start_date = fromdate
    end_date = todate

    # Create a list of all dates within the range
    all_dates = pd.date_range(start=start_date, end=end_date)



    # Convert existing_dates to datetime objects
    existing_dates = pd.to_datetime(existing_dates)

    # Find the missing dates
    missing_dates = all_dates[~all_dates.isin(existing_dates)]

    # Convert missing_dates to a list of strings
    missing_dates_list = missing_dates.strftime('%Y-%m-%d').tolist()

    #print("Missing dates:", missing_dates_list)
    return missing_dates_list




banknifty_data['date'] = pd.to_datetime(banknifty_data['date'])
existing_dates = banknifty_data['date'].unique()
datemissing = GetMissingDatesInRange(banknifty_data['date'].min(), banknifty_data['date'].max(), existing_dates)
datemissing = pd.to_datetime(datemissing)




# Initialize the Dash app
app = Dash(__name__)

# Layout of the Dash app
app.layout = html.Div([
    html.H1("BankNifty Event Days Candlestick Charts"),
    dcc.Slider(
        id='chart-slider',
        min=0,
        max=len(significant_days) - 1,
        value=0,
        marks={i: f'Event {i + 1}' for i in range(len(significant_days))},
        step=1,
    ),
    dcc.Graph(id='candlestick-chart')
])

# Callback to update the chart based on slider value
@app.callback(
    Output('candlestick-chart', 'figure'),
    [Input('chart-slider', 'value')]
)
def update_chart(slider_value):
    event_day = significant_days.iloc[slider_value]
    event_date = event_day['date']
    previous_date = event_day['previous_day']
    next_date = event_day['next_day']

    # Filter data for the event day, previous day, and next day
    days_to_plot = banknifty_data[(banknifty_data['date'] >= previous_date) & (banknifty_data['date'] <= next_date)]

    # Create subplots: 3 rows, 1 column
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.05,
                        subplot_titles=('Candlestick', 'AD Line (Weighted) with EMA 9', 'Weighted Volume'))

    # Candlestick chart
    fig.add_trace(go.Candlestick(x=days_to_plot['datetime'],
                                 open=days_to_plot['open'],
                                 high=days_to_plot['high'],
                                 low=days_to_plot['low'],
                                 close=days_to_plot['close']),
                  row=1, col=1)

    # AD Line with EMA 9
    fig.add_trace(go.Scatter(x=days_to_plot['datetime'], y=days_to_plot['AD_LineWeighted'],
                             mode='lines', name='AD Line (Weighted)'),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=days_to_plot['datetime'], y=days_to_plot['ema_9'],
                             mode='lines', name='EMA 9', line=dict(color='orange')),
                  row=2, col=1)

    # Weighted Volume with color change based on close price movement
    fig.add_trace(go.Bar(x=days_to_plot['datetime'], y=days_to_plot['weighted_volume'],
                         name='Weighted Volume',
                         marker=dict(color=days_to_plot['volume_color'])),
                  row=3, col=1)

    fig.update_layout(title=f'BankNifty from {previous_date.strftime("%Y-%m-%d")} to {next_date.strftime("%Y-%m-%d")}',
                      xaxis_title='Date',
                      yaxis_title='Price',
                      xaxis_rangeslider_visible=False)

    # Range breaks for non-trading hours, weekends, and missing dates
    rangebreaks = [dict(bounds=[15.45, 9.15], pattern="hour"), dict(bounds=["sat", "mon"]), dict(values=datemissing)]
    fig.update_xaxes(rangebreaks=rangebreaks)

    # Update layout dimensions
    fig.update_layout(height=800, width=1700)

    return fig

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)

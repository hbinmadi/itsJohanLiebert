import sqlite3
import pandas as pd
import plotly.graph_objects as go
import psutil
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, Input, Output, State, callback_context
import gc
import time
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


# Add previous and next days
def find_nearest_day(df, target_date, direction='previous'):
    if direction == 'previous':
        return df[df['date'] < target_date]['date'].max() or target_date
    elif direction == 'next':
        return df[df['date'] > target_date]['date'].min() or target_date


significant_days = one_sided_days
significant_days['previous_day'] = significant_days['date'].apply(
    lambda x: find_nearest_day(daily_range, x, 'previous'))
significant_days['next_day'] = significant_days['date'].apply(lambda x: find_nearest_day(daily_range, x, 'next'))

# Calculate the AD Line (weighted) and its EMA, along with weighted volume
banknifty_data['ema_9'] = banknifty_data['AD_LineWeighted'].ewm(span=9, adjust=False).mean()

# Determine whether the close is higher or lower than the previous close
banknifty_data['volume_color'] = [
    'green' if banknifty_data['close'].iloc[i] >= banknifty_data['open'].iloc[i] else 'red'
    for i in range(len(banknifty_data))]

# Step 1: Ensure date columns are in datetime format
banknifty_data['date'] = pd.to_datetime(banknifty_data['date'])
significant_days['date'] = pd.to_datetime(significant_days['date'])
significant_days['previous_day'] = pd.to_datetime(significant_days['previous_day'])
significant_days['next_day'] = pd.to_datetime(significant_days['next_day'])





# Step 2: Create a list of unique dates to keep in banknifty_data
unique_dates = pd.concat([
    significant_days['date'],
    significant_days['previous_day'],
    significant_days['next_day']
]).unique()

# Step 3: Filter banknifty_data to keep only the rows with dates in the unique_dates list
banknifty_data = banknifty_data[banknifty_data['date'].isin(unique_dates)]

# Reset the index
significant_days.reset_index(drop=True, inplace=True)

significant_days.to_csv("significant_days.csv")

# Write the DataFrame to the SQLite database
# If the table already exists, you can replace it or append to it.
banknifty_data.to_sql('banknifty_data', conn, if_exists='replace', index=False)

# Close the connection
conn.close()

def GetMissingDatesInRange(fromdate, todate, existing_dates):
    start_date = fromdate
    end_date = todate

    all_dates = pd.date_range(start=start_date, end=end_date)
    existing_dates = pd.to_datetime(existing_dates)
    missing_dates = all_dates[~all_dates.isin(existing_dates)]
    missing_dates_list = missing_dates.strftime('%Y-%m-%d').tolist()

    return missing_dates_list
#
#
# banknifty_data['date'] = pd.to_datetime(banknifty_data['date'])
# existing_dates = banknifty_data['date'].unique()
# datemissing = GetMissingDatesInRange(banknifty_data['date'].min(), banknifty_data['date'].max(), existing_dates)
# datemissing = pd.to_datetime(datemissing)

del banknifty_data



print("Loading data is called.... once")



# Initialize the Dash app
app = Dash(__name__)

# Update slider marks dynamically
app.layout = html.Div([
    dcc.Graph(id='candlestick-chart'),
    dcc.Slider(
        id='chart-slider',
        min=0,
        max=len(significant_days) - 1,
        value=0,
        marks={i: significant_days['date'].iloc[i].strftime('%Y-%m-%d') for i in range(len(significant_days))},
        step=1,
    ),
    html.Div([
        html.Button('Previous', id='previous-button', n_clicks=0),
        html.Button('Next', id='next-button', n_clicks=0)
    ]),
])

@app.callback(
    Output('candlestick-chart', 'figure'),
    [Input('chart-slider', 'value')]
)
def update_chart(slider_value):
    try:
        # Memory usage before processing
        #start_time = time.time()



        process = psutil.Process()
        mem_before = process.memory_info().rss / (1024 ** 2)
        print(f"Memory usage before processing: {mem_before:.2f} MB",slider_value)

        event_day = significant_days.iloc[slider_value]
        event_date, previous_date, next_date = event_day['date'], event_day['previous_day'], event_day['next_day']

        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)


        # Query the data for the selected date range
        query = f"""
                SELECT * 
                FROM banknifty_data 
                WHERE DATE(date) IN ('{previous_date.strftime("%Y-%m-%d")}', '{event_date.strftime("%Y-%m-%d")}', '{next_date.strftime("%Y-%m-%d")}')
                """
        #print(query)
        days_to_plot = pd.read_sql_query(query, conn)
        #print(days_to_plot)
        # Close the connection
        conn.close()
        days_to_plot['date'] = pd.to_datetime(days_to_plot['date'])
        # Find existing dates
        # existing_dates = days_to_plot['date'].unique()
        #
        # # Calculate missing dates within the selected range
        # # Find the missing dates within the range
        # datemissing = GetMissingDatesInRange(days_to_plot['date'].min(), days_to_plot['date'].max(), existing_dates)
        #
        # # Convert missing dates back to datetime format
        # datemissing = pd.to_datetime(datemissing)
        # print('datemissing',datemissing)
        # Filter the data
        #days_to_plot = banknifty_data[(banknifty_data['date'] >= previous_date) & (banknifty_data['date'] <= next_date)]

        # Initialize the figure
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.7, 0.15, 0.15], vertical_spacing=0.02)

        # Candlestick chart
        fig.add_trace(go.Candlestick(x=days_to_plot['datetime'],
                                     open=days_to_plot['open'],
                                     high=days_to_plot['high'],
                                     low=days_to_plot['low'],
                                     close=days_to_plot['close'],
                                     increasing_line_color='green',  # Color for increasing candles
                                     decreasing_line_color='black',  # Color for decreasing candles
                                     increasing_fillcolor='green',  # Solid color for increasing candles
                                     decreasing_fillcolor='black'  # Solid color for decreasing candles
                                     ),
                      row=1, col=1)

        # AD Line (Weighted)
        fig.add_trace(go.Scatter(x=days_to_plot['datetime'], y=days_to_plot['AD_LineWeighted'],
                                 mode='lines', name='AD Line (Weighted)'),
                      row=2, col=1)

        # EMA 9
        fig.add_trace(go.Scatter(x=days_to_plot['datetime'], y=days_to_plot['ema_9'],
                                 mode='lines', name='EMA 9', line=dict(color='green')),
                      row=2, col=1)

        # Weighted Volume
        fig.add_trace(go.Bar(x=days_to_plot['datetime'], y=days_to_plot['weighted_volume'],
                             name='Weighted Volume',
                             marker=dict(color=days_to_plot['volume_color'])),
                      row=3, col=1)

        # Update layout
        fig.update_layout(title=f'BankNifty from {previous_date.strftime("%Y-%m-%d")} to {next_date.strftime("%Y-%m-%d")}',
                          xaxis_title='Date :' + str(event_date),
                          yaxis_title='Price',
                          xaxis_rangeslider_visible=False,
                          height=750, width=1800)

        # # Update range breaks
        #rangebreaks = [dict(bounds=[15.45, 9.15], pattern="hour"), dict(bounds=["sat", "mon"]), dict(values=datemissing)]
        #fig.update_xaxes(rangebreaks=rangebreaks)

        fig.update_xaxes(type='category') ### this fixes the issue i spent the whole day on

        fig.update_xaxes(
            showticklabels=False  # Hide all x-axis labels
        )

        # Identify the end of each day (EOD)
        eod_times = days_to_plot.groupby(days_to_plot['date'].dt.date)['datetime'].max()

        # Add vertical lines at EOD
        for eod in eod_times:
            fig.add_shape(
                type="line",
                x0=eod, x1=eod,
                y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color="Blue", width=1, dash="dot")
            )

        # Memory usage after processing
        mem_after = process.memory_info().rss / (1024 ** 2)
        print(f"Memory usage after processing: {mem_after:.2f} MB")
        print(f"Memory used for this execution: {mem_after - mem_before:.2f} MB")

        # Cleanup: Delete unnecessary objects and run garbage collection
        del days_to_plot
        #del datemissing
        #del rangebreaks
        gc.collect()

        end_time = time.time()
        #print(f"Callback execution time: {end_time - start_time:.2f} seconds")
        #print("Figure generated:", fig)
        return fig

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return go.Figure()


# Callback to move slider value up or down based on button clicks
@app.callback(
    Output('chart-slider', 'value'),
    [Input('previous-button', 'n_clicks'),
     Input('next-button', 'n_clicks')],
    [State('chart-slider', 'value')]
)
def move_slider(previous_clicks, next_clicks, current_value):
    ctx = callback_context

    # Debugging: print the current state
    print("Current Value:", current_value)
    print("Previous Clicks:", previous_clicks)
    print("Next Clicks:", next_clicks)

    if not ctx.triggered:
        return current_value

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Debugging information
    print("Button ID:", button_id)
    print("Length of significant_days:", len(significant_days))

    if button_id == 'previous-button':
        new_value = max(0, current_value - 1)
    elif button_id == 'next-button':
        new_value = min(len(significant_days) - 1, current_value + 1)
    else:
        new_value = current_value

    # Ensure that the new value is within the bounds
    new_value = max(0, min(new_value, len(significant_days) - 1))

    # Print the new value for debugging
    print("New Value:", new_value)

    return new_value
import io
# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True, port=8051)


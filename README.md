BankNifty Event Days Candlestick Charts
This Dash application visualizes significant event days in the BankNifty index using candlestick charts. The app identifies days with significant one-sided movements of 500 points or more and allows you to navigate through these events, viewing the price action for the event day, the previous day, and the next day. Additionally, the app plots the AD Line (weighted) with its 9-period EMA and the weighted volume.

Features
Candlestick Charts: Visualize the price action of BankNifty on significant event days.
Event Navigation: Use the slider or buttons to navigate through identified significant days.
AD Line and EMA: View the AD Line (weighted) and its 9-period EMA on the same chart.
Volume Analysis: Analyze the weighted volume with color coding based on price movement.
Requirements
Python 3.7 or later
SQLite database with BankNifty data
Required Python packages:
dash
plotly
pandas
sqlite3 (built-in with Python)
Installation
Clone the Repository:

bash
Copy code
git clone https://github.com/yourusername/banknifty-candlestick-app.git
cd banknifty-candlestick-app
Install Dependencies:

Make sure you have a virtual environment set up, then install the required packages:

bash
Copy code
pip install dash plotly pandas
Prepare the SQLite Database:

Ensure your SQLite database file (IntradayGGData.db) is in the data directory, with a banknifty table containing the necessary columns (datetime, open, high, low, close, AD_LineWeighted, weighted_volume).

Run the Application:

bash
Copy code
python app.py
The app will start a server on http://127.0.0.1:8751/. Open this URL in your web browser to interact with the app.

Usage
Navigate Event Days: Use the slider or the "Previous" and "Next" buttons to view different event days.
Zoom and Pan: Use Plotly's built-in zoom and pan features to explore the chart in more detail.
Analyze Trends: Observe how the AD Line, EMA, and volume interact with price movements across different event days.
Code Structure
app.py: The main application script containing all the logic for loading data, processing it, and displaying the charts in a Dash app.
data/IntradayGGData.db: SQLite database file containing the historical BankNifty data (not included in the repository).
README.md: Documentation for the project.
Customization
Database Path: Update the db_path variable in app.py if your SQLite database is located elsewhere.
Significant Move Threshold: Modify the 500 point threshold in the script if you want to analyze different levels of significant moves.
UI Enhancements: Customize the layout, add more plots, or include additional data insights to meet your specific needs.
Troubleshooting
Database Connection Issues: Ensure the database file path is correct and that the database is not locked by another process.
Missing Data: If you encounter errors related to missing data, check that all required columns are present and populated in your SQLite table.
License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
Dash - The web framework used for this application.
Plotly - The graphing library used for creating interactive charts.

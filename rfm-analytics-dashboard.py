import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from datetime import datetime

# Read the dataset
data = pd.read_csv("rfm-analysis.csv")

# Convert 'PurchaseDate' to datetime
data['PurchaseDate'] = pd.to_datetime(data['PurchaseDate'], dayfirst=True, errors='coerce')
data = data.dropna(subset=['PurchaseDate'])  # Drop rows with invalid dates

# Calculate Recency
data['Recency'] = (datetime.now() - data['PurchaseDate']).dt.days

# Calculate Frequency
frequency_data = data.groupby('CustomerID')['OrderID'].count().reset_index()
frequency_data.rename(columns={'OrderID': 'Frequency'}, inplace=True)
data = data.merge(frequency_data, on='CustomerID', how='left')

# Calculate Monetary Value
monetary_data = data.groupby('CustomerID')['TransactionAmount'].sum().reset_index()
monetary_data.rename(columns={'TransactionAmount': 'MonetaryValue'}, inplace=True)
data = data.merge(monetary_data, on='CustomerID', how='left')

# Define scoring criteria for each RFM value
recency_scores = [5, 4, 3, 2, 1]  # Higher score for lower recency (more recent)
frequency_scores = [1, 2, 3, 4, 5]  # Higher score for higher frequency
monetary_scores = [1, 2, 3, 4, 5]  # Higher score for higher monetary value

# Calculate RFM scores
data['RecencyScore'] = pd.cut(data['Recency'], bins=5, labels=recency_scores).astype(int)
data['FrequencyScore'] = pd.cut(data['Frequency'], bins=5, labels=frequency_scores).astype(int)
data['MonetaryScore'] = pd.cut(data['MonetaryValue'], bins=5, labels=monetary_scores).astype(int)

# Calculate RFM score by combining the individual scores
data['RFM_Score'] = data['RecencyScore'] + data['FrequencyScore'] + data['MonetaryScore']

# Create RFM segments
segment_labels = ['Low-Value', 'Mid-Value', 'High-Value']
data['Value Segment'] = pd.qcut(data['RFM_Score'], q=3, labels=segment_labels)

# Create RFM Customer Segments
data['RFM Customer Segments'] = ''
data.loc[data['RFM_Score'] >= 9, 'RFM Customer Segments'] = 'Champions'
data.loc[(data['RFM_Score'] >= 6) & (data['RFM_Score'] < 9), 'RFM Customer Segments'] = 'Potential Loyalists'
data.loc[(data['RFM_Score'] >= 5) & (data['RFM_Score'] < 6), 'RFM Customer Segments'] = 'At Risk Customers'
data.loc[(data['RFM_Score'] >= 4) & (data['RFM_Score'] < 5), 'RFM Customer Segments'] = "Can't Lose"
data.loc[(data['RFM_Score'] >= 3) & (data['RFM_Score'] < 4), 'RFM Customer Segments'] = "Lost"

# Create Graphs
# 1. RFM Value Segment Distribution
segment_counts = data['Value Segment'].value_counts().reset_index()
segment_counts.columns = ['Value Segment', 'Count']
fig_segment_dist = px.bar(
    segment_counts,
    x='Value Segment',
    y='Count',
    color='Value Segment',
    color_discrete_sequence=px.colors.qualitative.Pastel,
    title='RFM Value Segment Distribution'
)

# 2. Treemap for Customer Segments
segment_product_counts = data.groupby(['Value Segment', 'RFM Customer Segments']).size().reset_index(name='Count')
fig_treemap_segment_product = px.treemap(
    segment_product_counts,
    path=['Value Segment', 'RFM Customer Segments'],
    values='Count',
    color='Value Segment',
    color_discrete_sequence=px.colors.qualitative.Pastel,
    title='RFM Customer Segments by Value'
)

# 3. Box Plot for Champions Segment
champions_segment = data[data['RFM Customer Segments'] == 'Champions']
champions_segment_fig = go.Figure()
champions_segment_fig.add_trace(go.Box(y=champions_segment['RecencyScore'], name='Recency'))
champions_segment_fig.add_trace(go.Box(y=champions_segment['FrequencyScore'], name='Frequency'))
champions_segment_fig.add_trace(go.Box(y=champions_segment['MonetaryScore'], name='Monetary'))
champions_segment_fig.update_layout(
    title='Distribution of RFM Values within Champions Segment',
    yaxis_title='RFM Value',
    showlegend=True
)

# 4. Correlation Heatmap
correlation_matrix = champions_segment[['RecencyScore', 'FrequencyScore', 'MonetaryScore']].corr()
fig_corr_heatmap = go.Figure(data=go.Heatmap(
    z=correlation_matrix.values,
    x=correlation_matrix.columns,
    y=correlation_matrix.columns,
    colorscale='RdBu',
    colorbar=dict(title='Correlation')
))
fig_corr_heatmap.update_layout(title='Correlation Matrix of RFM Values within Champions Segment')

# Build Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H1("RFM Analytics Dashboard", style={'text-align': 'center'}),
    dcc.Dropdown(
        id='graph-dropdown',
        options=[
            {'label': 'RFM Value Segment Distribution', 'value': 'segment_dist'},
            {'label': 'RFM Customer Segments Treemap', 'value': 'treemap'},
            {'label': 'RFM Values in Champions Segment', 'value': 'champions_box'},
            {'label': 'Correlation Matrix of Champions Segment', 'value': 'heatmap'},
        ],
        value='segment_dist',
        style={'width': '50%', 'margin': 'auto'}
    ),
    html.Div(id='graph-container', children=[])
])

@app.callback(
    Output('graph-container', 'children'),
    Input('graph-dropdown', 'value')
)
def update_graph(selected_graph):
    if selected_graph == 'segment_dist':
        return dcc.Graph(figure=fig_segment_dist)
    elif selected_graph == 'treemap':
        return dcc.Graph(figure=fig_treemap_segment_product)
    elif selected_graph == 'champions_box':
        return dcc.Graph(figure=champions_segment_fig)
    elif selected_graph == 'heatmap':
        return dcc.Graph(figure=fig_corr_heatmap)

# Run App
if __name__ == '__main__':
    app.run_server(debug=True)

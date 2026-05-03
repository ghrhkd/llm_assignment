import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

def create_interactive_compass(csv_path="quality_scores.csv", output_html="interactive_compass.html"):
    if not os.path.exists(csv_path):
        print(f"ERROR: File not found: {csv_path}. Please run the evaluation script first!")
        return

    # Step 1: Read data
    df = pd.read_csv(csv_path)

    # Step 2: Compute statistics with configured thresholds
    musiq_warning_line = 74.5
    niqe_warning_line = 7.0
    
    total_samples = len(df)
    # Filter out anomalies: MUSIQ too low OR NIQE too high
    anomalies_df = df[(df['MUSIQ_Score'] < musiq_warning_line) | (df['NIQE_Score'] > niqe_warning_line)]
    anomaly_count = len(anomalies_df)
    # Calculate percentage, avoid division by zero
    anomaly_percentage = (anomaly_count / total_samples) * 100 if total_samples > 0 else 0

    # Dynamically assemble title HTML with computed statistics
    dynamic_title = (
        f"<b>AIGC Virtual Try-On Quality Compass</b><br><br>"
        f"<sup>Total Samples: <b>{total_samples}</b> &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; "
        f"Anomalies Detected: <b>{anomaly_count}</b> &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; "
        f"Anomaly Rate: <b><span style='color:red'>{anomaly_percentage:.1f}%</span></b></sup>"
    )

    # Step 4: Create interactive scatter plot
    # X-axis: MUSIQ (higher is better), Y-axis: NIQE (lower is better)
    fig = px.scatter(
        df,
        x="MUSIQ_Score",
        y="NIQE_Score",
        hover_name="Filename",
        hover_data={"MUSIQ_Score": ':.2f', "NIQE_Score": ':.2f'},
        title=dynamic_title, # Use dynamically generated title
        labels={
            "MUSIQ_Score": "MUSIQ Structural Integrity (Higher is Better)",
            "NIQE_Score": "NIQE Naturalness Score (Lower is Better)"
        },
        template="plotly_white"
    )

    # Step 5: Beautify data points
    fig.update_traces(
        marker=dict(
            size=10,
            color='#1f77b4',
            line=dict(width=1, color='DarkSlateGrey'),
            opacity=0.8
        )
    )

    # Draw crosshair threshold warning lines
    # Add vertical MUSIQ warning line
    fig.add_vline(
        x=musiq_warning_line,
        line_width=2,
        line_dash="dash",
        line_color="orange",
        annotation_text="<-- Structural Failure Zone", 
        annotation_position="top left"
    )

    # Add horizontal NIQE warning line
    fig.add_hline(
        y=niqe_warning_line, 
        line_width=2, 
        line_dash="dash", 
        line_color="red",
        annotation_text="High Noise / Artifact Warning Zone -->", 
        annotation_position="top right"
    )

    # Mark "Baseline Quality Zone" (bottom-right corner)
    fig.add_annotation(
        x=df['MUSIQ_Score'].max(), 
        y=df['NIQE_Score'].min(),
        text="* Baseline Quality Zone",
        showarrow=False,
        font=dict(size=16, color="green"),
        xanchor="right",
        yanchor="bottom",
        opacity=0.6
    )

    # Step 8: Save HTML and auto-open in browser
    fig.write_html(output_html)
    print(f"Compass generated! Saved to: {output_html}")
    
    # Try to auto-open in browser
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.realpath(output_html))
    except:
        print(f"Please open {output_html} manually in your browser.")

if __name__ == "__main__":
    create_interactive_compass()
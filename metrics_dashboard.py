import pandas as pd
import plotly.express as px
from database import read_database

def dashboard(html_file_path="dashboard.html", database_path="database.json"):
    # 1. Fetch and prepare data
    data = read_database(database_path)
    
    df_pets = pd.DataFrame(data.get("posted_pets", []))
    df_posts = pd.json_normalize(
        data.get("posts", []),
        record_path=["metrics"],
        meta=["pet_id", "platform", "post_id", "post_url"],
    )
    
    df_metrics = pd.merge(df_pets, df_posts, on="pet_id", how="left")
    
    # Process views daily aggregations
    df_metrics["day"] = pd.to_datetime(df_metrics["collected_at"]).dt.tz_localize(None).dt.normalize()
    views = (
        df_metrics[["day", "platform", "post_id", "likes", "reposts", "comments"]]
        .groupby(["day", "platform", "post_id"])
        .max()
        .reset_index()
    )
    views = views.groupby(["day", "platform"])[["likes", "reposts", "comments"]].sum().reset_index()

    # 2. Options Setup
    platforms_html = ["All Platforms"] + sorted(
        [str(p) for p in df_metrics["platform"].dropna().unique() if p != "All Platforms"]
    )
    time_ranges = {
        "7d": "Last 7 Days",
        "28d": "Last 28 Days",
        "1y": "Last Year",
        "all": "All Time",
    }

    # 3. Build Dropdowns
    platform_options_html = "".join(
        [f'<option value="{p}">{p}</option>' for p in platforms_html]
    )
    timerange_options_html = "".join(
        [f'<option value="{key}">{label}</option>' for key, label in time_ranges.items()]
    )

    # 4. Determine max date and cutoff windows
    max_date = views["day"].max() if not views.empty else pd.Timestamp.now().normalize()
    cutoff_dates = {
        "all": None,
        "7d": max_date - pd.Timedelta(days=6),
        "28d": max_date - pd.Timedelta(days=27),
        "1y": max_date - pd.Timedelta(days=364),
    }

    # 5. Build HTML Sections
    sections_html = ""
    for p in platforms_html:
        p_df = df_metrics if p == "All Platforms" else df_metrics[df_metrics["platform"] == p]
        
        # --- SEPARATE TOP 5 CHARTS FOR LIKES, REPOSTS, COMMENTS ---
        top_charts_html = ""
        for metric in ["likes", "reposts", "comments"]:
            top_pets = (
                p_df.groupby(["pet_id", "name"])[metric]
                .sum()
                .reset_index()
                .sort_values(by=metric, ascending=False)
                .head(5)
            )
            
            fig_top = px.bar(
                top_pets,
                x="name",
                y=metric,
                title=f"Top 5 Pets by {metric.capitalize()} ({p})",
                labels={"name": "Pet Name", metric: f"Total {metric.capitalize()}"},
            )
            top_charts_html += fig_top.to_html(full_html=False, include_plotlyjs=False)

        # --- METRICS CHARTS PER TIME RANGE ---
        p_views = views if p == "All Platforms" else views[views["platform"] == p]

        metrics_html_by_range = ""
        for range_key in time_ranges.keys():
            cutoff = cutoff_dates[range_key]
            
            if cutoff is not None and not p_views.empty:
                full_dates = pd.date_range(start=cutoff, end=max_date, freq="D")
                unique_platforms = p_views["platform"].unique()
                idx = pd.MultiIndex.from_product([full_dates, unique_platforms], names=["day", "platform"])
                
                filtered_views = (
                    p_views.set_index(["day", "platform"])
                    .reindex(idx, fill_value=0)
                    .reset_index()
                )
            else:
                filtered_views = p_views

            metrics_charts = ""
            for metric in ["likes", "reposts", "comments"]:
                fig_metric = px.line(
                    filtered_views,
                    x="day",
                    y=metric,
                    color="platform" if p == "All Platforms" else None,
                    title=f"Total {metric.capitalize()} Over Time ({p} - {time_ranges[range_key]})",
                    labels={"day": "Date", metric: metric.capitalize()},
                )
                fig_metric.update_xaxes(tickangle=45, dtick="D1" if range_key == "7d" else None)
                metrics_charts += fig_metric.to_html(full_html=False, include_plotlyjs=False)

            is_default_range = "block" if range_key == "7d" else "none"
            metrics_html_by_range += f"""
            <div id="metrics-{p}-{range_key}" class="metrics-range-section metrics-{p}" style="display: {is_default_range};">
                {metrics_charts}
            </div>
            """

        is_default_platform = "block" if p == "All Platforms" else "none"
        sections_html += f"""
        <div id="platform-{p}" class="platform-section" style="display: {is_default_platform};">
            <h2>Top 5 Overall</h2>
            {top_charts_html}
            <hr style="margin: 30px 0;">
            <h3>Metrics Over Time</h3>
            <div style="margin-bottom: 20px;">
                <label for="timerange-select"><strong>Date Range:</strong> </label>
                <select id="timerange-select" onchange="updateDashboard()">
                    {timerange_options_html}
                </select>
            </div>
            {metrics_html_by_range}
        </div>
        """

    # 6. Construct complete HTML file
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cute Pets Boston Metrics Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .controls {{ margin-bottom: 25px; }}
            select {{ padding: 8px; font-size: 16px; }}
        </style>
    </head>
    <body>
        <h1>Cute Pets Boston Top Pets & Metrics</h1>
        
        <div class="controls">
            <label for="platform-select"><strong>Platform:</strong> </label>
            <select id="platform-select" onchange="updateDashboard()">
                {platform_options_html}
            </select>
        </div>

        {sections_html}

        <script>
            function updateDashboard() {{
                var selectedPlatform = document.getElementById('platform-select').value;
                var activePlatform = document.getElementById('platform-' + selectedPlatform);
                
                var activeRangeSelect = activePlatform.querySelector('#timerange-select');
                var selectedRange = activeRangeSelect ? activeRangeSelect.value : '7d';

                var platformSections = document.getElementsByClassName('platform-section');
                for (var i = 0; i < platformSections.length; i++) {{
                    platformSections[i].style.display = 'none';
                }}
                if (activePlatform) {{
                    activePlatform.style.display = 'block';
                }}

                var metricSections = document.getElementsByClassName('metrics-range-section');
                for (var j = 0; j < metricSections.length; j++) {{
                    metricSections[j].style.display = 'none';
                }}
                var activeMetrics = document.getElementById('metrics-' + selectedPlatform + '-' + selectedRange);
                if (activeMetrics) {{
                    activeMetrics.style.display = 'block';
                }}
            }}
        </script>
    </body>
    </html>
    """

    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Dashboard saved to {html_file_path}")

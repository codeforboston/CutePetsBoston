import pandas as pd
import plotly.express as px
from database import _read_database


def dashboard(html_file_path="dashboard.html"):
    # 1. Fetch data
    data = _read_database(database_path="database.json")

    df_posts = pd.json_normalize(
        data["posts"],
        record_path=["metrics"],  # Unpacks the nested metrics array
        meta=[
            "pet_id",
            "platform",
            "post_id",
            "post_url",
            "posted_at",
        ],  # Carries along parent post info
    )
    
    # Create DataFrames for both sections
    df_pets = pd.DataFrame(data["posted_pets"])
    
    df_posts = pd.json_normalize(
        data["posts"],
        record_path=["metrics"],
        meta=["pet_id", "platform", "post_id", "post_url"],
    )
    
    # Merge pets metadata with detailed post metrics
    df_metrics = pd.merge(df_pets, df_posts, on="pet_id", how="left")
    
    # 2. Get unique platforms including 'All Platforms'
    platforms_html = ["All Platforms"] + sorted(
        [
            str(p)
            for p in df_metrics["platform"].dropna().unique()
            if p != "All Platforms"
        ]
    )
    
    # 3. Build options HTML for the dropdown
    dropdown_options = "".join(
        [f'<option value="{p}">{p}</option>' for p in platforms_html]
    )
    
    # 4. Generate HTML blocks for each platform and metric
    sections_html = ""
    for p in platforms_html:
      if p == "All Platforms":
        filtered_platform_temp = df_metrics
      else:
        filtered_platform_temp = df_metrics[df_metrics["platform"] == p]
    
      platform_charts_html = ""
    
      for col in ["likes", "reposts", "comments"]:
        temp = (
            filtered_platform_temp[["post_id", "pet_id", "name", col]]
            .groupby(["post_id", "pet_id", "name"])
            .max()
            .reset_index()
        )
    
        agg_temp = (
            temp[["pet_id", "name", col]]
            .groupby(["pet_id", "name"])[col]
            .agg(["max", "sum"])
            .reset_index()
        )
    
        temp1 = agg_temp.sort_values("max", ascending=False).head(10)
        temp2 = agg_temp.sort_values("sum", ascending=False).head(10)
    
        metric_label = col.capitalize()
    
        fig_max = px.bar(
            data_frame=temp1,
            x="name",
            y="max",
            title=f"Top 10 Pets by Max {metric_label} [{p}]",
            labels={"name": "Pet", "max": f"Max {metric_label}"},
        )
        fig_sum = px.bar(
            data_frame=temp2,
            x="name",
            y="sum",
            title=f"Top 10 Pets by Total {metric_label} [{p}]",
            labels={"name": "Pet", "sum": f"Total {metric_label}"},
        )
    
        platform_charts_html += f"""
            <div class="chart-container">{fig_max.to_html(full_html=False, include_plotlyjs='cdn' if (p == platforms_html[0] and col == 'likes') else False)}</div>
            <div class="chart-container">{fig_sum.to_html(full_html=False, include_plotlyjs=False)}</div>
            """
    
      display_style = "block" if p == platforms_html[0] else "none"
      sections_html += f"""
        <div class="platform-section" id="section-{p}" style="display: {display_style};">
            {platform_charts_html}
        </div>
        """
    
    # 5. Assemble full HTML document with styling and switching logic
    html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Cute Pets Boston Top Pets</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; background-color: #f9f9f9; }}
            h1 {{ color: #333; }}
            .dropdown-container {{ margin-bottom: 30px; }}
            select {{ padding: 8px 15px; font-size: 16px; border-radius: 4px; border: 1px solid #ccc; }}
            .chart-container {{ margin-bottom: 30px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: inline-block; width: 80%; max-width: 800px; }}
        </style>
        <script>
            function filterPlatform(selectedPlatform) {{
                var sections = document.getElementsByClassName('platform-section');
                for (var i = 0; i < sections.length; i++) {{
                    sections[i].style.display = 'none';
                }}
                var activeSection = document.getElementById('section-' + selectedPlatform);
                if (activeSection) {{
                    activeSection.style.display = 'block';
                }}
            }}
        </script>
    </head>
    <body>
        <h1>🐶 Cute Pets Boston Top Pets 🐶</h1>
        <div class="dropdown-container">
            <label for="platform-select"><strong>Select Platform: </strong></label>
            <select id="platform-select" onchange="filterPlatform(this.value)">
                {dropdown_options}
            </select>
        </div>
        {sections_html}
    </body>
    </html>
    """
    
    # 6. Write out file
    with open(html_file_path, "w", encoding="utf-8") as f:
      f.write(html_content)
    
    print(
        "Successfully generated dashboard.html with all platforms, max/sum stats,"
        " and metrics!"
    )


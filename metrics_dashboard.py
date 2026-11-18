from pathlib import Path

import pandas as pd
import plotly.express as px
from itables import to_html_datatable

from database import PostedPet, read_database


def adoption_table_html(pets: list[PostedPet]) -> str:
    if not pets:
        return ""
    rows = []
    seen_ids: set[str] = set()
    for pet in pets:
        pet_id = str(pet.get("pet_id") or "").strip()
        if pet_id and pet_id in seen_ids:
            continue
        seen_ids.add(pet_id)
        rows.append(
            {
                "Name": pet["name"],
                "Pet ID": pet_id,
                "Posted date": pet["posted_at"][:10],
                "Adoption status": pet.get("status_name") or "Unknown",
                "Status last observed": pet.get("status_observed_at", "")[:10],
            }
        )
    frame = pd.DataFrame(rows)
    summary = (
        frame.groupby("Adoption status")
        .size()
        .rename("Pets")
        .reset_index()
        .to_html(index=False, table_id="adoption-status-summary", border=0)
    )
    table = to_html_datatable(
        frame,
        table_id="adoption-status-table",
        showIndex=False,
        allow_html=False,
        maxBytes=0,
        display_logo_when_loading=False,
        layout={"topStart": "pageLength", "topEnd": "search", "bottomStart": "info", "bottomEnd": "paging"},
        pageLength=10,
        order=[[2, "desc"]],
    )
    return f"""<section>
        <h2>Posted pet adoption statuses</h2>
        <p>Statuses are the last successfully observed shelter reports.
        Unknown means no status has been retrieved. Dates are in UTC;
        the observation date is not the actual adoption date.</p>
        <h3>Pet counts by status</h3>
        <div style="display: inline-block; text-align: left;">{summary}</div>
        {table}
    </section>"""


def empty_dashboard_html(message: str, adoption_html: str = "") -> str:
    return f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Cute Pets Boston Top Pets</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; background-color: #f9f9f9; }}
            h1 {{ color: #333; }}
        </style>
    </head>
    <body>
        <h1>🐶 Cute Pets Boston Top Pets 🐶</h1>
        {adoption_html}
        <p>{message}</p>
    </body>
    </html>
    """


def dashboard(
    html_file_path: str | Path = "dashboard.html",
    database_path: str | Path = "database.json",
) -> None:
    # 1. Fetch data
    data = read_database(database_path)
    posts = data.get("posts", [])
    posted_pets = data.get("posted_pets", [])
    adoption_html = adoption_table_html(posted_pets)

    if not posts or not posted_pets:
        with open(html_file_path, "w", encoding="utf-8") as f:
            message = "No engagement data available yet." if posted_pets else "No analytics data available yet."
            f.write(empty_dashboard_html(message, adoption_html))
        return

    df_pets = pd.DataFrame(posted_pets)
    df_posts = pd.json_normalize(
        [dict(post) for post in posts],
        record_path=["metrics"],  # Unpacks the nested metrics array
        meta=["pet_id", "platform", "post_id", "post_url"],
    )

    # Merge pets metadata with detailed post metrics
    df_metrics = pd.merge(df_pets, df_posts, on="pet_id", how="left")

    # Posts with no recorded metrics yet leave the metric columns absent
    missing = [col for col in ("likes", "reposts", "comments") if col not in df_metrics.columns]
    df_metrics = df_metrics.reindex(columns=[*df_metrics.columns, *missing])

    if not df_metrics["likes"].notna().any():
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(empty_dashboard_html("No metric data available yet.", adoption_html))
        return

    # 2. Get unique platforms including 'All Platforms'
    platforms_html = ["All Platforms"] + sorted(
        [str(p) for p in df_metrics["platform"].dropna().unique() if p != "All Platforms"]
    )

    # 3. Build options HTML for the dropdown
    dropdown_options = "".join([f'<option value="{p}">{p}</option>' for p in platforms_html])

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

            agg_temp = temp[["pet_id", "name", col]].groupby(["pet_id", "name"])[col].agg(["max", "sum"]).reset_index()

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
            <div class="chart-container">{fig_max.to_html(full_html=False, include_plotlyjs="cdn" if (p == platforms_html[0] and col == "likes") else False)}</div>
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
        {adoption_html}
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

    print("Successfully generated dashboard.html with all platforms, max/sum stats, and metrics!")


if __name__ == "__main__":
    dashboard()

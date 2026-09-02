import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# Automatically grabs your repo owner in GitHub Actions, fallback for local testing
USERNAME = os.getenv("GITHUB_REPOSITORY_OWNER", "Sayak-Bhattasali")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""

def fetch_data():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    res = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": USERNAME}},
        headers=headers
    )
    if res.status_code != 200 or "data" not in res.json():
        raise Exception(f"GraphQL query failed: {res.text}")
    return res.json()["data"]["user"]

def calculate_sparkline(weeks, width=640, height=45):
    counts = [day["contributionCount"] for w in weeks for day in w["contributionDays"]]
    if not counts:
        return ""
    max_c = max(counts) or 1
    step = width / (len(counts) - 1) if len(counts) > 1 else width

    points = []
    for i, count in enumerate(counts):
        x = round(i * step, 1)
        # Invert Y coordinate for SVG space
        y = round(height - ((count / max_c) * (height - 8)) - 4, 1)
        points.append(f"{x},{y}")
    return " ".join(points)

def generate_stats_svg(data, output_path):
    calendar = data["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    weeks = calendar["weeks"]

    # Calculate active days
    all_days = [day for w in weeks for day in w["contributionDays"]]
    active_days = sum(1 for d in all_days if d["contributionCount"] > 0)

    # Calculate top languages
    lang_totals = {}
    for repo in data["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_totals[name] = lang_totals.get(name, 0) + edge["size"]

    top_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:4]
    total_bytes = sum(lang_totals.values()) or 1
    sparkline_points = calculate_sparkline(weeks, width=640, height=45)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 230" width="100%" height="auto">
  <style>
    .mono {{ font-family: "JetBrains Mono", Consolas, monospace; fill: #8b949e; font-size: 11px; }}
    .highlight {{ fill: #58a6ff; font-weight: bold; }}
    .number {{ fill: #f0f6fc; font-size: 32px; font-weight: bold; }}
    .sub {{ font-size: 11px; fill: #7d8590; }}
    .spark {{ fill: none; stroke: #58a6ff; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }}
  </style>
  <rect width="100%" height="100%" fill="#0d1117" rx="8" />

  <!-- Contributions Counter -->
  <text x="30" y="55" class="mono number">{total}</text>
  <text x="30" y="78" class="mono sub">contributions in the last year</text>

  <text x="540" y="48" class="mono number" font-size="22">{active_days}</text>
  <text x="540" y="68" class="mono sub">active days</text>

  <!-- Sparkline Graph -->
  <g transform="translate(30, 95)">
    <polyline points="{sparkline_points}" class="spark">
      <animate attributeName="opacity" from="0" to="1" dur="0.8s" fill="freeze" />
    </polyline>
  </g>

  <!-- Top Languages by Bytes -->
  <text x="30" y="172" class="mono" font-size="10" fill="#58a6ff">TOP LANGUAGES</text>
"""
    x_pos = 30
    for name, size in top_langs:
        pct = int((size / total_bytes) * 100)
        svg += f"""
  <text x="{x_pos}" y="195" class="mono" fill="#f0f6fc">{name.lower()}</text>
  <text x="{x_pos}" y="210" class="mono sub">{pct}%</text>
"""
        x_pos += 150

    svg += "</svg>"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_file = os.path.join(base_dir, "assets", "stats.svg")

    if GITHUB_TOKEN:
        data = fetch_data()
        generate_stats_svg(data, out_file)
        print("[OK] Generated assets/stats.svg")
    else:
        print("[!] GITHUB_TOKEN not detected locally. GitHub Actions will run this on push.")

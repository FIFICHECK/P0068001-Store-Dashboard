#!/usr/bin/env python3
"""Replace the <style> block in index.html with MUJI-style theme."""
import re

PATH = "/home/snkwok/P0068001-Store-Dashboard/index.html"

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

MUJI_CSS = """<style>
  :root {
    --bg: #f7f4ee;
    --bg-card: #ffffff;
    --bg-hover: #f3efe8;
    --bg-soft: #faf8f4;
    --border: #e2ddd3;
    --text: #2f2f2f;
    --text-dim: #8a857e;
    --accent: #c1002e;
    --accent-dark: #9e0026;
    --green: #4a7c59;
    --yellow: #b58900;
    --qty: #5b6770;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: "Helvetica Neue", Helvetica, Arial, "PingFang HK", "Microsoft JhengHei", sans-serif;
    min-height: 100vh;
  }
  .container { max-width: 1480px; margin: 0 auto; padding: 24px 20px 60px; }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    padding: 14px 0 18px;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 26px;
  }
  .logo {
    background: var(--accent);
    color: #fff;
    padding: 8px 14px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 2px;
    flex-shrink: 0;
  }
  .title-block { display: flex; align-items: center; gap: 16px; }
  h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: 0.5px; color: var(--text); }
  .subtitle { color: var(--text-dim); font-size: 0.85rem; margin-top: 3px; letter-spacing: 0.3px; }
  .store-badge {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  .store-badge strong { color: var(--text); font-weight: 600; }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 20px 24px;
  }
  .stat-label { color: var(--text-dim); font-size: 0.8rem; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; letter-spacing: 0.3px; }
  .stat-value { font-size: 1.7rem; font-weight: 700; letter-spacing: 0.5px; color: var(--text); }
  .stat-value.money { color: var(--accent); }
  .stat-sub { color: var(--text-dim); font-size: 0.78rem; margin-top: 6px; }

  .panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 24px 26px;
    margin-bottom: 28px;
  }
  .panel-title {
    font-size: 1.1rem; font-weight: 700;
    margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px;
    color: var(--text);
    letter-spacing: 0.3px;
  }
  .panel-desc { color: var(--text-dim); font-size: 0.82rem; margin-bottom: 20px; }
  .chart-wrap { position: relative; height: 320px; }

  .table-scroll { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; border-collapse: collapse; min-width: 560px; }
  thead th {
    text-align: left;
    font-size: 0.78rem;
    color: var(--text-dim);
    font-weight: 600;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    white-space: nowrap;
    letter-spacing: 0.3px;
  }
  tbody td {
    padding: 12px;
    font-size: 0.9rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    color: var(--text);
  }
  tbody tr:hover { background: var(--bg-soft); }
  td .date { font-weight: 700; color: var(--text); }
  td .gmv-val { color: var(--accent); font-weight: 600; }
  .badge-final {
    background: rgba(74, 124, 89, 0.12);
    color: var(--green);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .badge-partial {
    background: rgba(181, 137, 0, 0.12);
    color: var(--yellow);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .dl-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-size: 0.8rem;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.15s;
  }
  .dl-btn:hover { background: var(--accent-dark); }

  footer {
    text-align: center;
    color: var(--text-dim);
    font-size: 0.75rem;
    padding-top: 20px;
    border-top: 1px solid var(--border);
  }
  .empty { text-align: center; color: var(--text-dim); padding: 40px 0; font-size: 0.9rem; }

  .monthly-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
  .monthly-card {
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .monthly-card .m-month { font-size: 1.05rem; font-weight: 700; color: var(--text); }
  .monthly-card .m-stats { color: var(--text-dim); font-size: 0.8rem; line-height: 1.7; }
  .monthly-card .m-stats strong { color: var(--text); }
  .monthly-card .m-gmv { color: var(--accent); font-weight: 700; font-size: 1.2rem; }
  .trend-controls {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 18px;
  }
  .sku-search {
    flex: 1;
    min-width: 200px;
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    padding: 10px 14px;
    font-size: 0.9rem;
    outline: none;
  }
  .sku-search:focus { border-color: var(--accent); }
  .sku-select {
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    padding: 10px 14px;
    font-size: 0.9rem;
    min-width: 280px;
    max-width: 100%;
    outline: none;
  }
  .sku-select:focus { border-color: var(--accent); }
  .trend-summary {
    display: flex;
    gap: 22px;
    flex-wrap: wrap;
    margin-bottom: 18px;
    font-size: 0.85rem;
  }
  .trend-summary .ts-item { color: var(--text-dim); }
  .trend-summary .ts-item strong { color: var(--text); font-weight: 700; }
  .trend-table-block { margin-top: 28px; }
  .trend-table-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }
  .tt-title { font-size: 0.98rem; font-weight: 700; color: var(--text); }
  .table-count {
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 0.75rem;
    color: var(--text-dim);
  }
  .trend-table-scroll {
    width: 100%;
    max-height: 420px;
    overflow-y: auto;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .trend-table {
    width: 100%;
    min-width: 720px;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  .trend-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f1ede5;
    color: var(--text-dim);
    font-weight: 600;
    text-align: left;
    padding: 9px 10px;
    border-bottom: 2px solid var(--border);
    white-space: nowrap;
    letter-spacing: 0.2px;
  }
  .trend-table thead th.date-group {
    text-align: center;
    background: #eae5db;
    color: var(--text);
  }
  .trend-table tbody td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    color: var(--text);
  }
  .trend-table tbody tr:hover { background: var(--bg-soft); }
  .trend-table td.sku-cell {
    font-weight: 600;
    color: var(--text);
    position: sticky;
    left: 0;
    background: var(--bg-card);
    z-index: 1;
  }
  .trend-table tbody tr:hover td.sku-cell { background: var(--bg-soft); }
  .trend-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .trend-table td.gmv-cell { color: var(--accent); }
  .trend-table td.qty-cell { color: var(--qty); }
  .trend-table td.total-gmv { font-weight: 700; color: var(--accent); }
  .trend-table td.total-qty { font-weight: 700; color: var(--qty); }

  @media (max-width: 480px) {
    h1 { font-size: 1.1rem; }
    .stat-value { font-size: 1.35rem; }
    .panel { padding: 16px; }
    .chart-wrap { height: 250px; }
  }
</style>"""

# Replace style block
start = content.index("<style>")
end = content.index("</style>") + len("</style>")
content = content[:start] + MUJI_CSS + content[end:]

# Logo: "MU" -> "MUJI"
content = content.replace('<div class="logo">MU</div>', '<div class="logo">MUJI</div>')

# Chart.js colors: main GMV chart (dark theme reds -> MUJI red)
content = content.replace("'rgba(231, 76, 60, 0.75)'", "'rgba(193, 0, 46, 0.75)'")
content = content.replace("'rgba(231, 76, 60, 1)'", "'rgba(193, 0, 46, 1)'")
content = content.replace("'rgba(52, 152, 219, 0.2)'", "'rgba(91, 103, 112, 0.2)'")
content = content.replace("'rgba(52, 152, 219, 1)'", "'rgba(91, 103, 112, 1)'")

# Chart ticks/grid colors
content = content.replace("color: '#9aa3b2'", "color: '#8a857e'")
content = content.replace("grid: { color: '#232833' }", "grid: { color: '#e2ddd3' }")
content = content.replace("color: '#e0e0e0'", "color: '#2f2f2f'")
content = content.replace("color: '#1b1f28'", "color: '#f1ede5'")

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("MUJI theme applied ✓")
print("Logo:", "MUJI" if 'class="logo">MUJI<' in content else "NOT CHANGED")

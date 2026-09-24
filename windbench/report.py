"""Build the interactive report: results/metrics.json injected into templates/report.html.

Writes results/report.html and docs/index.html (the copy GitHub Pages serves).
"""
from pathlib import Path

from .config import DOCS_DIR, RESULTS_DIR

TEMPLATE = Path(__file__).with_name("templates") / "report.html"


def main(argv=None):
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", (RESULTS_DIR / "metrics.json").read_text())
    DOCS_DIR.mkdir(exist_ok=True)
    for out in (RESULTS_DIR / "report.html", DOCS_DIR / "index.html"):
        out.write_text(html)
        print(f"wrote {out} ({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()

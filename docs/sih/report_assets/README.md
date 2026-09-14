# Rebuilding `Inayat_Internal_Screening_Report.pdf`

Not part of the app - these scripts generate the PDF in
`docs/sih/Inayat_Internal_Screening_Report.pdf` and are kept here purely
so the document is reproducible from source, matching this project's
convention for its other SIH-facing PDFs.

Deliberately uses a separate virtualenv, not the project's own
`.venv`/`requirements.txt`: `matplotlib` is a real dependency for
generating the report's charts and architecture diagram, but it is not
a dependency of the actual application, and this project does not add
one-off documentation tooling to its production requirements files.

```bash
python3 -m venv /tmp/report-venv
source /tmp/report-venv/bin/activate
pip install matplotlib reportlab

python3 build_charts.py         # writes chart_*.png into the cwd
python3 build_architecture.py   # writes architecture.png into the cwd
python3 build_report.py         # reads those PNGs, writes the PDF
```

Run them from this directory (or update the hardcoded output paths at
the top of each script) - `build_report.py` expects
`chart_consultation_time.png`, `chart_threshold.png`,
`chart_eval_composition.png`, and `architecture.png` to already exist
alongside it.

Every number in the report is either measured directly from this
repository's own code/tests (re-run `pytest -q` and re-check
`data/evaluation/test_cases.json` before reusing old figures) or drawn
from an external source cited in the report's own References section -
if you update a claim, update its source too.

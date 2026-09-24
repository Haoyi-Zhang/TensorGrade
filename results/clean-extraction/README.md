# Clean-extraction verification record

This directory records the final same-environment verification run made from
fresh extractions of the project and standalone-repository archives. The
scientific output is in `run/`; `reproduced-summary.json` is the reconciled
summary; `tex-tables/` contains the nine regenerated manuscript tables; and
`logs/` contains command output plus semantic-summary, table, and rendered-PDF
comparisons.

The clean scientific summary matches `../summary.json` after excluding only the
environment-dependent CPU-time and peak-RSS fields. All nine tables are
byte-identical to the manuscript inputs. The clean main and supplement rebuilds
have 36 and 10 pages, respectively, and their 96-dpi page renders are identical
to the visually inspected retained PDFs.

This is a same-environment packaging/reproduction check, not independent human
replication, proof-assistant verification, cross-platform validation, or upstream
Scorch execution.

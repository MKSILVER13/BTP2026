# Indian Kanoon Scraper

Interactive catalogue scraper for public Indian Kanoon laws and judgments. It downloads the main document and Indian Kanoon’s available structural classification.

## Install

From PowerShell:

```powershell
cd E:\Docs\intern\AAintern\legal\indian_kanoon_fetcher
python -m pip install -e .
```

## Interactive scraper

Start the numbered menu:

```powershell
python -m ik_scraper --output data --delay 1
```

Example commands inside the menu:

```text
1       Open Browse Laws or Browse Judgments option 1
#1      Download every document under option 1
b       Go back one level
h       Return to the home menu
q       Quit
```

The scraper asks for confirmation before downloading a category. Use `--max-documents` for a small test:

```powershell
python -m ik_scraper --output test-data --delay 1 --max-documents 2
```

## One-time website inventory

Create a document-level CSV inventory without downloading full document text:

```powershell
python -m ik_scraper --inventory --output inventory --delay 1
```

Inventory files:

```text
inventory\website-inventory.csv
inventory\website-category-summary.csv
inventory\website-type-year-summary.csv
inventory\website-inventory-errors.csv
```

## Downloaded files

Documents are stored below `data\laws\` or `data\judgments\`. Each document may contain:

```text
<document-id>.txt
<document-id>.json
<document-id>.classified.txt
```

The classified file uses labels such as `fact`, `issue`, `appellant_argument`, `court_reasoning`, and `conclusion`. Existing files are skipped on later runs, so interrupted downloads can be rerun.

Use a conservative delay and document limit. The scraper requests ordinary public pages only and does not bypass access controls.

# IBBI Government PDF Fetcher

The scraper reads public order tables from configured IBBI subsections and downloads linked PDFs. It does not depend on the inaccessible `/orders` landing page.

## Install

From PowerShell:

```powershell
cd E:\Docs\intern\AAintern\legal\ibbi_gov_fetcher
python -m pip install -e .
```

## Examples

Scan the first NCLAT page without downloading PDFs:

```powershell
python -m ibbi_gov_fetcher --section nclat --output ibbi_data
```

Download page 2 only:

```powershell
python -m ibbi_gov_fetcher --section nclat --page 2 --download --output ibbi_data
```

Download every NCLAT page:

```powershell
python -m ibbi_gov_fetcher --section nclat --all-pages --download --output ibbi_data
```

Download a small test batch:

```powershell
python -m ibbi_gov_fetcher --section nclat --all-pages --download --max-documents 5 --output test-data
```

Download all configured sections:

```powershell
python -m ibbi_gov_fetcher --all-sections --all-pages --download --output ibbi_data
```

Use a custom section configuration:

```powershell
python -m ibbi_gov_fetcher --config sections.json --all-sections --all-pages --download --output ibbi_data
```

## Output

Without `--download`, the tool performs a dry run and creates metadata reports only. With `--download`, PDFs are stored below `ibbi_data\pdf\`.

Reports are written to:

```text
ibbi_data\reports\ibbi-unified-documents.csv
ibbi_data\reports\ibbi-section-summary.csv
ibbi_data\reports\ibbi-errors.csv
```

The unified CSV includes the section, page, serial number, order date, subject, order remarks, PDF URL, local filename, download status, file size, SHA-256 hash, and errors. Existing PDFs are skipped on later runs.

Use a conservative delay and document limit. The scraper requests ordinary public pages only and does not bypass access controls.

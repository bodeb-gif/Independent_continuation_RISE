"""Audit and extract Philadelphia Fed real-time snapshots for ProQuest models.

No current-vintage values are backfilled into historical features. Public
workbooks stay unchanged. Run --fetch once, then rebuild the audit offline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import pandas as pd

OUT = Path("data/scored/proquest/macro_information")
REFERENCE = OUT / "reference"
BASE = "https://www.philadelphiafed.org"
FILE_BASE = BASE + "/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/"
SOURCES = {
    "IPT": {"file": "iptMvMd.xlsx", "url": FILE_BASE + "xlsx/iptMvMd.xlsx",
            "page": BASE + "/surveys-and-data/real-time-data-research/ipt",
            "documentation": FILE_BASE + "documentation/doc_ip.pdf", "frequency": "monthly",
            "quantity": "Total industrial production index, seasonally adjusted; base varies by vintage"},
    "RUC": {"file": "rucQvMd.xlsx", "url": FILE_BASE + "xlsx/rucQvMd.xlsx",
            "page": BASE + "/surveys-and-data/real-time-data-research/ruc",
            "documentation": FILE_BASE + "RUC/specific_documentation_RUC.pdf", "frequency": "quarterly",
            "quantity": "Civilian unemployment rate, seasonally adjusted, percentage points"},
    "CPI": {"file": "cpiQvMd.xlsx", "url": FILE_BASE + "xlsx/cpiQvMd.xlsx",
            "page": BASE + "/surveys-and-data/real-time-data-research/cpi",
            "documentation": FILE_BASE + "CPI/specific_documentation_CPI.pdf", "frequency": "quarterly",
            "quantity": "Consumer price index, seasonally adjusted; within-vintage percentage changes"},
}
CORE_FEATURES = ("ip_growth_3m", "ip_growth_6m", "ip_growth_12m", "ip_age_months",
                 "unemployment_level", "unemployment_change_3m", "unemployment_change_12m", "unemployment_age_months")
CPI_FEATURES = ("cpi_change_3m", "cpi_change_12m", "cpi_age_months")
NAMESPACE = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def vintage_date(name):
    match = re.fullmatch(r"(IPT|RUC|CPI)(\d{2})([MQ])(\d{1,2})", name)
    if not match:
        raise ValueError(f"Unrecognized vintage header: {name}")
    _, year, frequency, number = match.groups()
    year, number = int(year), int(number)
    year += 1900 if year >= 62 else 2000
    if frequency == "M":
        if not 1 <= number <= 12:
            raise ValueError("Invalid vintage month")
        # Documentation gives the release month, not an exact day in the header.
        # Month end is a conservative public-availability bound, never midmonth.
        month = pd.Period(f"{year}-{number:02}", "M")
        return month.end_time.normalize()
    if not 1 <= number <= 4:
        raise ValueError("Invalid vintage quarter")
    return pd.Timestamp(year, 3 * number - 1, 15)


def xlsx_rows(path):
    """Read source cells without rewriting a workbook or using cached formulas.

    The IPT workbook has date-only document metadata that openpyxl rejects.
    XML cell extraction ignores that unrelated metadata and retains raw values.
    """
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.itertext()) for node in root.findall("x:si", NAMESPACE)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall("x:sheets/x:sheet", NAMESPACE)
        if len(sheets) != 1:
            raise ValueError(f"Expected one data sheet in {path}")
        relationship = sheets[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(node.get("Target") for node in rels if node.get("Id") == relationship)
        member = target.lstrip("/") if target.startswith("/") else urljoin("xl/", target)
        with archive.open(member) as source:
            for _, node in ET.iterparse(source, events=("end",)):
                if node.tag != "{" + NAMESPACE["x"] + "}row":
                    continue
                cells = {}
                for cell in node.findall("x:c", NAMESPACE):
                    if cell.find("x:f", NAMESPACE) is not None:
                        raise ValueError("Unexpected formula in source vintage data")
                    address = cell.attrib["r"]
                    letters = re.match(r"[A-Z]+", address)[0]
                    raw = cell.find("x:v", NAMESPACE)
                    value = raw.text if raw is not None else None
                    if cell.get("t") == "s" and value is not None:
                        value = strings[int(value)]
                    elif cell.get("t") == "inlineStr":
                        value = "".join(cell.find("x:is", NAMESPACE).itertext())
                    cells[letters] = value
                yield cells
                node.clear()


def read_vintage_workbook(path, series, cutoff="2010-12-01"):
    rows = iter(xlsx_rows(path))
    header = next(rows)
    if header.get("A") != "DATE":
        raise ValueError(f"Expected DATE in A1: {path}")
    selected = {column: name for column, name in header.items()
                if column != "A" and name and name.startswith(series) and vintage_date(name) < pd.Timestamp(cutoff)}
    observations, records = [], []
    for row in rows:
        date = row.get("A")
        if not date:
            continue
        if not re.fullmatch(r"\d{4}:\d{2}", date):
            raise ValueError(f"Unexpected observation label: {date}")
        observation = pd.Period(date.replace(":", "-"), "M")
        if observation >= pd.Period(cutoff, "M"):
            continue
        observations.append(observation)
        records.append([float(row[column]) if row.get(column) not in {None, "", "#N/A", "NA"} else np.nan for column in selected])
    matrix = pd.DataFrame(records, index=pd.PeriodIndex(observations, freq="M"), columns=list(selected.values()))
    if not matrix.index.is_unique or not matrix.columns.is_unique:
        raise ValueError("Duplicate observation/vintage coordinates")
    return matrix


class VintageSeries:
    def __init__(self, name, matrix):
        self.name = name
        self.matrix = matrix
        self.dates = {column: vintage_date(column) for column in matrix}

    def snapshot(self, origin):
        """Most recent nonempty snapshot strictly before the first day of origin."""
        day = pd.Period(origin, "M").start_time
        eligible = [c for c in self.matrix if self.dates[c] < day and self.matrix[c].notna().any()]
        if not eligible:
            return None, None
        name = max(eligible, key=self.dates.get)
        return name, self.matrix[name].dropna()


def load_archives():
    archives, source_records, audit = {}, {}, []
    for name, source in SOURCES.items():
        path = REFERENCE / source["file"]
        matrix = read_vintage_workbook(path, name)
        archives[name] = VintageSeries(name, matrix)
        available = [c for c in matrix if matrix[c].notna().any()]
        first = min(available, key=vintage_date)
        last = max(available, key=vintage_date)
        source_records[name] = {**source, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        audit.append({"series": name, "quantity": source["quantity"], "vintage_frequency": source["frequency"],
                      "first_nonempty_vintage": first, "first_availability_bound": str(vintage_date(first).date()),
                      "last_used_vintage": last, "nonempty_vintages": len(available),
                      "empty_vintage_columns": len(matrix.columns) - len(available),
                      "first_forecast_origin": str(vintage_date(first).to_period("M") + 1), "source_url": source["page"]})
    return archives, source_records, pd.DataFrame(audit)


def macro_features(archives, origins):
    rows = []
    for origin in origins:
        row = {"origin": origin, **{feature: np.nan for feature in CORE_FEATURES + CPI_FEATURES}}
        for name, archive in archives.items():
            vintage, snapshot = archive.snapshot(origin)
            row[f"{name}_vintage"] = vintage
            row[f"{name}_available_by"] = str(archive.dates[vintage].date()) if vintage else None
            row[f"{name}_latest_observation"] = str(snapshot.index.max()) if vintage else None
            if vintage is None:
                continue
            latest = snapshot.index.max()
            if latest >= origin:
                raise ValueError("Macro snapshot contains a current/future observation")
            age = origin.ordinal - latest.ordinal
            def change(months, percentage=True):
                earlier = snapshot.get(latest - months, np.nan)
                current = snapshot.loc[latest]
                if pd.isna(earlier) or (percentage and earlier <= 0):
                    return np.nan
                return 100 * (current / earlier - 1) if percentage else current - earlier
            if name == "IPT":
                for months in (3, 6, 12):
                    row[f"ip_growth_{months}m"] = change(months)
                row["ip_age_months"] = age
            elif name == "RUC":
                row["unemployment_level"] = snapshot.loc[latest]
                for months in (3, 12):
                    row[f"unemployment_change_{months}m"] = change(months, percentage=False)
                row["unemployment_age_months"] = age
            else:
                for months in (3, 12):
                    row[f"cpi_change_{months}m"] = change(months)
                row["cpi_age_months"] = age
        row["core_available"] = all(pd.notna(row[f]) for f in CORE_FEATURES)
        row["cpi_available"] = row["core_available"] and all(pd.notna(row[f]) for f in CPI_FEATURES)
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_sources(retrieved_date):
    import requests
    REFERENCE.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, source in SOURCES.items():
        path = REFERENCE / source["file"]
        if not path.exists():
            response = requests.get(source["url"], timeout=90)
            response.raise_for_status()
            if not response.content.startswith(b"PK"):
                raise ValueError("Expected an XLSX ZIP container")
            path.write_bytes(response.content)
        doc_path = REFERENCE / f"{name}_documentation.pdf"
        if not doc_path.exists():
            response = requests.get(source["documentation"], timeout=90)
            response.raise_for_status()
            doc_path.write_bytes(response.content)
        manifest[name] = {**source, "retrieved_date": retrieved_date,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "documentation_sha256": hashlib.sha256(doc_path.read_bytes()).hexdigest()}
    (REFERENCE / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--retrieved-date", default="2026-10-14")
    args = parser.parse_args()
    if args.fetch:
        fetch_sources(args.retrieved_date)
    archives, sources, audit = load_archives()
    origins = pd.period_range("1950-01", "2010-12", freq="M")
    features = macro_features(archives, origins)
    OUT.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUT / "vintage_coverage.csv", index=False)
    features.to_csv(OUT / "macro_feature_audit.csv", index=False)
    for name, archive in archives.items():
        archive.matrix.rename_axis("observation_month").to_csv(OUT / f"{name}_vintages_through_2010.csv.gz", compression={"method": "gzip", "mtime": 0})
    (OUT / "availability_audit.json").write_text(json.dumps({"sources": sources,
        "rule": "No backward fills; select latest nonempty vintage strictly before forecast-month start. IPT uses month-end availability bound; quarterly RUC/CPI use February/May/August/November 15.",
        "core_first_origin": str(features.loc[features.core_available, "origin"].min()),
        "cpi_first_origin": str(features.loc[features.cpi_available, "origin"].min()),
        "core_months": int(features.core_available.sum()), "cpi_months": int(features.cpi_available.sum()),
        "local_revised_snapshots": "Prior frozen INDPRO/UNRATE/CPI snapshots have no vintage dimension and are rejected as historical predictor inputs."}, indent=2) + "\n")
    print(audit.to_string(index=False))
    print(features.groupby(features.origin.dt.year // 10 * 10)[["core_available", "cpi_available"]].sum().to_string())


if __name__ == "__main__":
    main()

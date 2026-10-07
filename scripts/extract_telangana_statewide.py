#!/usr/bin/env python3
"""
Phase 2 — Telangana-Wide Historical Procurement ETL Script
Extracts, normalizes, classifies, deduplicates, and validates historical procurement records for the ENTIRE Telangana State.

Outputs:
    - data/processed/telangana_historical_all.csv
    - data/processed/telangana_historical_review.csv
    - docs/telangana-historical-etl-report.md
"""

import sys
import os
import csv
import logging
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.etl.historical_source import HistoricalSourceReader
from backend.etl.telangana_filter import TelanganaFilter
from backend.etl.project_classifier import ProjectClassifier
from backend.etl.normalizer import ETLNormalizer
from backend.etl.deduplicator import ETLDeduplicator
from backend.etl.validator import ETLValidator
from backend.etl.loader import HistoricalETLLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ALL_CSV_PATH = "data/processed/telangana_historical_all.csv"
REVIEW_CSV_PATH = "data/processed/telangana_historical_review.csv"
REPORT_MD_PATH = "docs/telangana-historical-etl-report.md"

def main():
    logger.info("Starting Phase 2 — Telangana-Wide Historical Procurement ETL Pipeline...")

    reader = HistoricalSourceReader()
    tg_filter = TelanganaFilter()
    classifier = ProjectClassifier()
    normalizer = ETLNormalizer()
    deduplicator = ETLDeduplicator()
    validator = ETLValidator()
    loader = HistoricalETLLoader(dry_run=True)

    db_path = reader.initialize()
    logger.info(f"Connected to Hugging Face SQLite dataset at: {db_path}")

    total_scanned = 0
    total_telangana = 0

    all_records = []
    review_records = []
    road_infra_records = []

    # Counters and maps
    cat_counts = Counter()
    org_counts = Counter()
    district_counts = Counter()
    year_telangana = Counter()
    year_road = Counter()

    uppal_hits = 0
    iiit_hits = 0

    chunk_size = 5000
    for chunk in reader.stream_records(chunk_size=chunk_size):
        total_scanned += len(chunk)

        for record in chunk:
            if not tg_filter.is_telangana_record(record):
                continue

            total_telangana += 1

            category, relevance, reason = classifier.classify(record)
            normalized = normalizer.normalize_record(record, category, relevance, reason)

            # Targeted test tracking (Uppal & IIIT)
            text_upper = f"{normalized.get('project_name', '')} {normalized.get('work_description', '')}".upper()
            if "UPPAL" in text_upper:
                uppal_hits += 1
            if "IIIT" in text_upper or "GACHIBOWLI" in text_upper:
                iiit_hits += 1

            # Extract year
            aoc_date = str(normalized.get("aoc_date") or "")
            year = "UNKNOWN"
            if len(aoc_date) >= 4 and aoc_date[:4].isdigit():
                year = aoc_date[:4]
            elif "-" in aoc_date and len(aoc_date.split("-")[-1][:4]) == 4 and aoc_date.split("-")[-1][:4].isdigit():
                year = aoc_date.split("-")[-1][:4]

            year_telangana[year] += 1

            is_dup, dup_key = deduplicator.process(normalized)
            quality_status = validator.validate_record(normalized, is_dup)

            normalized["quality_status"] = quality_status
            normalized["deduplication_key"] = dup_key

            # Accumulate metrics
            cat_counts[category] += 1
            org_counts[normalized.get("organisation") or "UNKNOWN"] += 1

            district = normalized.get("district") or "NOT_FOUND"
            district_counts[district] += 1

            if category != "NOT_RELEVANT" and category != "OTHER_INFRASTRUCTURE":
                road_infra_records.append(normalized)
                year_road[year] += 1
                all_records.append(normalized)
            else:
                review_records.append(normalized)

    # Dry-run loader notification
    loader.load_records(all_records + review_records)

    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    csv_fields = [
        "project_candidate_key", "project_name", "work_description", "category",
        "state", "district", "city", "municipality", "locality", "location_text",
        "organisation", "department", "executing_authority", "tender_id",
        "tender_reference_number", "tender_title", "tender_publication_date",
        "tender_closing_date", "contractor", "selected_bidder", "contract_value",
        "award_date", "completion_period", "source_name", "source_type",
        "source_record_id", "source_url", "retrieved_at", "quality_status", "relevance_rating"
    ]

    # Save Cleaned Statewide CSV
    with open(ALL_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in all_records:
            writer.writerow(r)

    logger.info(f"Saved statewide dataset ({len(all_records):,} records) to {ALL_CSV_PATH}")

    # Save Review CSV
    with open(REVIEW_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in review_records:
            writer.writerow(r)

    logger.info(f"Saved review dataset ({len(review_records):,} records) to {REVIEW_CSV_PATH}")

    # Coverage metrics calculation
    total_relevant = len(road_infra_records) if road_infra_records else 1
    contractor_pct = (sum(1 for r in road_infra_records if r.get("contractor")) / total_relevant) * 100
    cost_pct = (sum(1 for r in road_infra_records if r.get("contract_value", 0) or r.get("awarded_value", 0)) / total_relevant) * 100
    ref_pct = (sum(1 for r in road_infra_records if r.get("tender_reference_number") and r.get("tender_reference_number") != "NOT_AVAILABLE") / total_relevant) * 100
    loc_pct = (sum(1 for r in road_infra_records if r.get("district") != "NOT_FOUND" or r.get("city") != "NOT_FOUND") / total_relevant) * 100

    valid_years = [int(y) for y in year_telangana.keys() if y.isdigit() and 2010 <= int(y) <= 2026]
    earliest_yr = str(min(valid_years)) if valid_years else "2018"
    latest_yr = str(max(valid_years)) if valid_years else "2026"

    # Generate Markdown Report
    md_content = f"""# Telangana-Wide Historical Procurement ETL Report

**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Source Dataset**: `fireboy21/tenders_aoc` (Hugging Face SQLite repository)  
**Database Status**: NOT MODIFIED (0 PostgreSQL imports)

---

## 1. Executive Summary & Dataset Totals

- **Total Source Records Scanned**: {total_scanned:,}
- **Total Telangana Records Identified**: {total_telangana:,}
- **Total Relevant Road/Infrastructure Records**: {len(road_infra_records):,}
- **Historical Coverage Range**: {earliest_yr} – {latest_yr}

---

## 2. Infrastructure Category Breakdown

| Category | Record Count | Percentage |
| :--- | :--- | :--- |
| **ROAD** | {cat_counts['ROAD']:,} | {(cat_counts['ROAD']/max(1, total_telangana))*100:.1f}% |
| **HIGHWAY** | {cat_counts['HIGHWAY']:,} | {(cat_counts['HIGHWAY']/max(1, total_telangana))*100:.1f}% |
| **FLYOVER** | {cat_counts['FLYOVER']:,} | {(cat_counts['FLYOVER']/max(1, total_telangana))*100:.1f}% |
| **GRADE_SEPARATOR** | {cat_counts['GRADE_SEPARATOR']:,} | {(cat_counts['GRADE_SEPARATOR']/max(1, total_telangana))*100:.1f}% |
| **BRIDGE** | {cat_counts['BRIDGE']:,} | {(cat_counts['BRIDGE']/max(1, total_telangana))*100:.1f}% |
| **ROB** | {cat_counts['ROB']:,} | {(cat_counts['ROB']/max(1, total_telangana))*100:.1f}% |
| **RUB** | {cat_counts['RUB']:,} | {(cat_counts['RUB']/max(1, total_telangana))*100:.1f}% |
| **ELEVATED_CORRIDOR** | {cat_counts['ELEVATED_CORRIDOR']:,} | {(cat_counts['ELEVATED_CORRIDOR']/max(1, total_telangana))*100:.1f}% |
| **ELEVATED_ROAD** | {cat_counts['ELEVATED_ROAD']:,} | {(cat_counts['ELEVATED_ROAD']/max(1, total_telangana))*100:.1f}% |
| **ROAD_WIDENING** | {cat_counts['ROAD_WIDENING']:,} | {(cat_counts['ROAD_WIDENING']/max(1, total_telangana))*100:.1f}% |
| **ROAD_DEVELOPMENT** | {cat_counts['ROAD_DEVELOPMENT']:,} | {(cat_counts['ROAD_DEVELOPMENT']/max(1, total_telangana))*100:.1f}% |
| **OTHER_INFRASTRUCTURE** | {cat_counts['OTHER_INFRASTRUCTURE']:,} | {(cat_counts['OTHER_INFRASTRUCTURE']/max(1, total_telangana))*100:.1f}% |

---

## 3. Discovered Organisations & Contracting Authorities

Total Discovered Organisations: **{len(org_counts):,}**

| Organisation | Total Records |
| :--- | :--- |
"""
    for org, count in org_counts.most_common(15):
        md_content += f"| **{org}** | {count:,} |\n"

    md_content += """
---

## 4. Statewide District & Location Coverage

Total Discovered Districts/Locations: **""" + f"{len(district_counts):,}**\n\n| District / Location | Record Count |\n| :--- | :--- |\n"
    for dist, count in district_counts.most_common(15):
        md_content += f"| **{dist}** | {count:,} |\n"

    md_content += f"""
---

## 5. Historical Date Range & Annual Breakdown

| Year | Total Telangana Records | Road / Infrastructure Records |
| :--- | :--- | :--- |
"""
    for yr in sorted(year_telangana.keys()):
        if yr != "UNKNOWN":
            md_content += f"| **{yr}** | {year_telangana[yr]:,} | {year_road[yr]:,} |\n"

    md_content += f"""
---

## 6. Statewide Data Quality & Completeness

- **Contractor Name Coverage**: {contractor_pct:.1f}%
- **Contract Value Coverage**: {cost_pct:.1f}%
- **Tender Reference Coverage**: {ref_pct:.1f}%
- **Location / District Coverage**: {loc_pct:.1f}%

---

## 7. Test Case Validation (Uppal & IIIT/Gachibowli)

- **Uppal Test Matches**: {uppal_hits:,} records
- **IIIT / Gachibowli Test Matches**: {iiit_hits:,} records

---

## 8. Output Deliverables

- Cleaned Statewide Historical Dataset: `data/processed/telangana_historical_all.csv` ({len(all_records):,} records)
- Review Dataset: `data/processed/telangana_historical_review.csv` ({len(review_records):,} records)
- Documentation Report: `docs/telangana-historical-etl-report.md`

---
*Report generated automatically by scripts/extract_telangana_statewide.py*
"""

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"Saved Markdown report to {REPORT_MD_PATH}")

    # Print Final Terminal Summary Output Box
    print("\n" + "=" * 50)
    print("TELANGANA-WIDE HISTORICAL ETL COMPLETE")
    print("=" * 50)
    print("")
    print(f"Source records scanned: {total_scanned:,}")
    print(f"Telangana records: {total_telangana:,}")
    print("")
    print(f"Relevant road/infrastructure records: {len(road_infra_records):,}")
    print("")
    print(f"ROAD: {cat_counts['ROAD']:,}")
    print(f"HIGHWAY: {cat_counts['HIGHWAY']:,}")
    print(f"FLYOVER: {cat_counts['FLYOVER']:,}")
    print(f"GRADE_SEPARATOR: {cat_counts['GRADE_SEPARATOR']:,}")
    print(f"BRIDGE: {cat_counts['BRIDGE']:,}")
    print(f"ROB: {cat_counts['ROB']:,}")
    print(f"RUB: {cat_counts['RUB']:,}")
    print(f"ELEVATED_CORRIDOR: {cat_counts['ELEVATED_CORRIDOR']:,}")
    print(f"ROAD_WIDENING: {cat_counts['ROAD_WIDENING']:,}")
    print(f"OTHER_INFRASTRUCTURE: {cat_counts['OTHER_INFRASTRUCTURE']:,}")
    print("")
    print(f"Organisations discovered: {len(org_counts):,}")
    print(f"Districts/locations discovered: {len(district_counts):,}")
    print("")
    print(f"Contractor coverage: {contractor_pct:.1f}%")
    print(f"Contract value coverage: {cost_pct:.1f}%")
    print(f"Tender reference coverage: {ref_pct:.1f}%")
    print(f"Location coverage: {loc_pct:.1f}%")
    print("")
    print(f"Earliest record: {earliest_yr}")
    print(f"Latest record: {latest_yr}")
    print("")
    print(f"Uppal test: {uppal_hits:,} matches")
    print(f"IIIT/Gachibowli test: {iiit_hits:,} matches")
    print("")
    print(f"Final statewide dataset:")
    print(f"data/processed/telangana_historical_all.csv")
    print("")
    print(f"Review dataset:")
    print(f"data/processed/telangana_historical_review.csv")
    print("")
    print(f"Report:")
    print(f"docs/telangana-historical-etl-report.md")
    print("")
    print("PostgreSQL:")
    print("NOT MODIFIED")
    print("")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()

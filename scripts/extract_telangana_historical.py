#!/usr/bin/env python3
"""
Telangana Historical Procurement ETL Script
Extracts, filters, classifies, normalizes, deduplicates, and validates historical tender data from fireboy21/tenders_aoc.

Usage:
    python scripts/extract_telangana_historical.py --dry-run
"""

import sys
import os
import argparse
import logging
import csv
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any

# Ensure project root is in sys.path
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

def parse_args():
    parser = argparse.ArgumentParser(description="Telangana Historical Procurement ETL Pipeline")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run ETL without writing to PostgreSQL")
    parser.add_argument("--limit", type=int, default=0, help="Limit scanned records (0 for all)")
    return parser.parse_args()

def main():
    args = parse_args()
    logger.info(f"Starting Telangana Historical Procurement ETL Pipeline (Dry Run: {args.dry_run})...")

    reader = HistoricalSourceReader()
    tg_filter = TelanganaFilter()
    classifier = ProjectClassifier()
    normalizer = ETLNormalizer()
    deduplicator = ETLDeduplicator()
    validator = ETLValidator()
    loader = HistoricalETLLoader(dry_run=args.dry_run)

    db_path = reader.initialize()
    logger.info(f"Connected to source SQLite dataset at: {db_path}")

    total_scanned = 0
    total_telangana = 0
    road_project_records = []
    all_processed_records = []

    # Category and status counters
    category_counts = Counter()
    quality_counts = Counter()
    org_counts = Counter()
    years_found = set()

    # Keyword hit tracking
    uppal_hits = 0
    iiit_hits = 0
    ghmc_hits = 0
    hmda_hits = 0
    rnb_hits = 0
    nhai_hits = 0

    chunk_size = 5000
    for chunk in reader.stream_records(chunk_size=chunk_size):
        total_scanned += len(chunk)

        for record in chunk:
            # 1. Filter for Telangana records
            if not tg_filter.is_telangana_record(record):
                continue

            total_telangana += 1

            # 2. Classify record
            category, relevance, reason = classifier.classify(record)

            # 3. Normalize record
            normalized = normalizer.normalize_record(record, category, relevance, reason)

            # Track targeted searches
            text_upper = f"{normalized.get('title', '')} {normalized.get('description', '')} {normalized.get('organisation', '')}".upper()
            
            if "UPPAL" in text_upper:
                uppal_hits += 1
            if "IIIT" in text_upper or "GACHIBOWLI" in text_upper:
                iiit_hits += 1
            if "GHMC" in text_upper or "GREATER HYDERABAD MUNICIPAL" in text_upper:
                ghmc_hits += 1
            if "HMDA" in text_upper or "HYDERABAD METROPOLITAN DEVELOPMENT" in text_upper:
                hmda_hits += 1
            if "ROADS & BUILDINGS" in text_upper or "R&B" in text_upper or "ROADS AND BUILDINGS" in text_upper:
                rnb_hits += 1
            if "NHAI" in text_upper or "NATIONAL HIGHWAYS AUTHORITY" in text_upper:
                nhai_hits += 1

            # Year extraction
            aoc_date = normalized.get("aoc_date") or ""
            if len(aoc_date) >= 4 and aoc_date[:4].isdigit():
                years_found.add(int(aoc_date[:4]))

            # 4. Deduplicate record
            is_dup, dup_key = deduplicator.process(normalized)

            # 5. Quality validation
            quality_status = validator.validate_record(normalized, is_dup)
            normalized["quality_status"] = quality_status
            normalized["deduplication_key"] = dup_key

            # Accumulate counters
            category_counts[category] += 1
            quality_counts[quality_status] += 1
            org_counts[normalized.get("organisation", "UNKNOWN")] += 1

            all_processed_records.append(normalized)
            if category in ["HIGHWAY / ROAD", "FLYOVER / GRADE SEPARATOR", "INFRASTRUCTURE"]:
                road_project_records.append(normalized)

        if total_scanned % 25000 == 0:
            logger.info(f"Progress: {total_scanned:,} scanned | {total_telangana:,} Telangana records found...")
            sys.stdout.flush()

        if args.limit and total_scanned >= args.limit:
            logger.info(f"Reached scanning limit of {args.limit:,} records.")
            break

    # Execute loader check
    loader.load_records(all_processed_records)

    # Output directories
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    csv_path = "data/processed/telangana_road_projects_preview.csv"
    doc_path = "docs/telangana-etl-preview.md"

    # Save Preview CSV
    csv_headers = [
        "tender_id", "tender_reference_number", "title", "organisation", "category",
        "relevance_rating", "quality_status", "original_contractor_name", "normalized_contractor_name",
        "awarded_value", "aoc_date", "completion_period", "matching_reason", "deduplication_key", "source_url"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
        writer.writeheader()
        for r in all_processed_records:
            writer.writerow(r)

    logger.info(f"Saved preview CSV with {len(all_processed_records):,} records to {csv_path}")

    # Generate Markdown Report
    years_str = f"{min(years_found)}–{max(years_found)}" if years_found else "N/A"
    
    val_with_contractor = sum(1 for r in all_processed_records if r.get("normalized_contractor_name"))
    val_with_cost = sum(1 for r in all_processed_records if r.get("awarded_value"))

    markdown_content = f"""# Telangana Historical Procurement ETL — Phase 2 Validation Report

**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Data Source**: `fireboy21/tenders_aoc` (Hugging Face SQLite dataset)  
**ETL Status**: READ-ONLY / DRY-RUN (0 database mutations)

---

## 1. Summary Statistics

| Metric | Value |
| :--- | :--- |
| **Total Scanned Records** | {total_scanned:,} |
| **Telangana Records Identified** | {total_telangana:,} |
| **Road & Project Relevant Records** | {len(road_project_records):,} |
| **Year Coverage Range** | {years_str} |
| **Records with Contractor Name** | {val_with_contractor:,} ({(val_with_contractor/max(1, total_telangana))*100:.1f}%) |
| **Records with Contract Value** | {val_with_cost:,} ({(val_with_cost/max(1, total_telangana))*100:.1f}%) |

---

## 2. Category Classification Breakdown

| Category | Record Count | Percentage |
| :--- | :--- | :--- |
| **HIGHWAY / ROAD** | {category_counts['HIGHWAY / ROAD']:,} | {(category_counts['HIGHWAY / ROAD']/max(1, total_telangana))*100:.1f}% |
| **FLYOVER / GRADE SEPARATOR** | {category_counts['FLYOVER / GRADE SEPARATOR']:,} | {(category_counts['FLYOVER / GRADE SEPARATOR']/max(1, total_telangana))*100:.1f}% |
| **INFRASTRUCTURE** | {category_counts['INFRASTRUCTURE']:,} | {(category_counts['INFRASTRUCTURE']/max(1, total_telangana))*100:.1f}% |
| **OTHER** | {category_counts['OTHER']:,} | {(category_counts['OTHER']/max(1, total_telangana))*100:.1f}% |

---

## 3. Data Quality & Completeness Status

| Quality Status | Count | Description |
| :--- | :--- | :--- |
| **VALID** | {quality_counts['VALID']:,} | Complete record with Tender ID, Title, Org, Contractor, and Awarded Value |
| **INCOMPLETE** | {quality_counts['INCOMPLETE']:,} | Partial record missing contractor name or exact financial value |
| **POSSIBLE_DUPLICATE** | {quality_counts['POSSIBLE_DUPLICATE']:,} | Record matching exact tender ID or reference number |
| **LOW_RELEVANCE** | {quality_counts['LOW_RELEVANCE']:,} | Record outside core road/highway infrastructure focus |

---

## 4. Targeted Keyword Matches

| Targeted Query / Entity | Hits Found | Description / Example Findings |
| :--- | :--- | :--- |
| **Uppal / Uppal Elevated Corridor** | {uppal_hits:,} | Infrastructure & road works in Uppal & Uppal-Ghatkesar corridor |
| **IIIT / Gachibowli** | {iiit_hits:,} | Flyover, junction improvement & road works in Gachibowli / IIIT area |
| **GHMC** | {ghmc_hits:,} | Municipal road construction, resurfacing & SRDP flyover projects |
| **HMDA** | {hmda_hits:,} | Outer Ring Road (ORR), radial roads & master plan infrastructure |
| **R&B (Roads & Buildings)** | {rnb_hits:,} | State highway widening, bridge construction & district connectivity |
| **NHAI (RO Hyderabad)** | {nhai_hits:,} | National Highway expansion, 4/6 laning & toll plaza infrastructure |

---

## 5. Major Contracting Organisations

"""
    top_orgs = org_counts.most_common(10)
    for org, count in top_orgs:
        markdown_content += f"- **{org}**: {count:,} records\n"

    markdown_content += """

---

## 6. Sample Extracted Records Preview

Below are sample normalized records extracted from the historical dataset:

"""
    sample_records = [r for r in all_processed_records if r.get("quality_status") == "VALID"][:5]
    if not sample_records:
        sample_records = all_processed_records[:5]

    for idx, r in enumerate(sample_records, 1):
        val_display = f"₹{r.get('awarded_value'):,.2f}" if r.get("awarded_value") else "N/A"
        markdown_content += f"""### Sample {idx}: {r.get('title')}
- **Tender Ref**: {r.get('tender_reference_number')}
- **Organisation**: {r.get('organisation')}
- **Category**: {r.get('category')}
- **Contractor**: {r.get('normalized_contractor_name')} (Original: `{r.get('original_contractor_name')}`)
- **Awarded Value**: {val_display}
- **AOC Date**: {r.get('aoc_date')}
- **Quality Status**: `{r.get('quality_status')}`
- **Source URL**: {r.get('source_url')}

"""

    markdown_content += """---
*Report generated automatically by Telangana Historical Procurement ETL Pipeline.*
"""

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    logger.info(f"Saved Markdown report to {doc_path}")

    # Output Terminal Summary Box
    print("\n" + "=" * 80)
    print("          TELANGANA HISTORICAL PROCUREMENT ETL - EXECUTION SUMMARY             ")
    print("=" * 80)
    print(f"  Data Source                  : fireboy21/tenders_aoc (Hugging Face)")
    print(f"  Total Dataset Records Scanned: {total_scanned:,}")
    print(f"  Telangana Records Found      : {total_telangana:,}")
    print(f"  Road & Project Records       : {len(road_project_records):,}")
    print("-" * 80)
    print("  CATEGORY BREAKDOWN:")
    print(f"   - Highway / Road            : {category_counts['HIGHWAY / ROAD']:,}")
    print(f"   - Flyover / Grade Separator : {category_counts['FLYOVER / GRADE SEPARATOR']:,}")
    print(f"   - Infrastructure            : {category_counts['INFRASTRUCTURE']:,}")
    print("-" * 80)
    print("  QUALITY STATUS:")
    print(f"   - VALID                     : {quality_counts['VALID']:,}")
    print(f"   - INCOMPLETE                : {quality_counts['INCOMPLETE']:,}")
    print(f"   - POSSIBLE_DUPLICATE        : {quality_counts['POSSIBLE_DUPLICATE']:,}")
    print(f"   - LOW_RELEVANCE             : {quality_counts['LOW_RELEVANCE']:,}")
    print("-" * 80)
    print("  TARGETED KEYWORD SEARCHES:")
    print(f"   - Uppal / Elevated Corridor : {uppal_hits:,} match(es)")
    print(f"   - IIIT / Gachibowli         : {iiit_hits:,} match(es)")
    print(f"   - GHMC                      : {ghmc_hits:,} match(es)")
    print(f"   - HMDA                      : {hmda_hits:,} match(es)")
    print(f"   - R&B                       : {rnb_hits:,} match(es)")
    print(f"   - NHAI                      : {nhai_hits:,} match(es)")
    print("-" * 80)
    print("  OUTPUT ARTIFACTS:")
    print(f"   - CSV Preview: {csv_path}")
    print(f"   - Documentation: {doc_path}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()

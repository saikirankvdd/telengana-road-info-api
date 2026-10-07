import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# Ensure DATABASE_URL defaults to local sqlite if Postgres not running
if "DATABASE_URL" not in os.environ or "postgresql" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite:///./telangana_road_intel.db"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.project import Project, ProjectContractor, ProjectTender, ProjectAuthority
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.models.authority import Authority
from backend.models.research import ResearchRun, ProjectResearchSource, ProjectFieldEvidence
from backend.models.research_merge import ResearchMergeReview, ResearchMergeAction
from backend.models.data_quality import ResearchQualityReportModel, ResearchQualityIssueModel
from backend.auth.models import UserModel
from backend.auth.schemas import UserRole
from backend.auth.service import AuthService

client = TestClient(app)
OUTPUT_DIR = "outputs/research_tests"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_auth_headers(db: Session) -> Dict[str, str]:
    admin = db.query(UserModel).filter(UserModel.role == UserRole.ADMIN.value).first()
    if not admin:
        admin = UserModel(
            username="accept_admin",
            email="accept_admin@telangana.gov.in",
            password_hash=AuthService.hash_password("AdminPass123!"),
            role=UserRole.ADMIN.value,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = AuthService.create_access_token(data={"sub": admin.username, "role": admin.role})
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": "tg_road_intel_secret_key_2026",
        "Content-Type": "application/json"
    }

def count_canonical_rows(db: Session) -> Dict[str, int]:
    return {
        "projects": db.query(Project).count(),
        "tenders": db.query(Tender).count(),
        "contractors": db.query(Contractor).count(),
        "authorities": db.query(Authority).count(),
        "project_contractors": db.query(ProjectContractor).count(),
        "project_tenders": db.query(ProjectTender).count(),
        "project_authorities": db.query(ProjectAuthority).count()
    }

def run_acceptance_test_case(
    case_num: int,
    file_name: str,
    project_query: str,
    db: Session,
    headers: Dict[str, str]
) -> Dict[str, Any]:
    print(f"\n==================================================")
    print(f"Executing Test Case {case_num}: '{project_query}'")
    print(f"==================================================")

    # 1. Health & Readiness Probe
    h_res = client.get("/health")
    assert h_res.status_code == 200, f"Health check failed: {h_res.text}"
    r_res = client.get("/ready")
    assert r_res.status_code == 200, f"Readiness check failed: {r_res.text}"

    # 2. Live Research Execution API
    start_time = time.time()
    res = client.post("/api/v1/research/project", json={"project_name": project_query, "force_refresh": True}, headers=headers)
    assert res.status_code == 200, f"Research API failed with status {res.status_code}: {res.text}"
    research_data = res.json()
    duration_s = time.time() - start_time

    # Resolve research run ID
    run_id = None
    if research_data.get("project_id") and str(research_data.get("project_id")).isdigit():
        run_id = int(research_data.get("project_id"))
    else:
        latest_run = db.query(ResearchRun).filter(ResearchRun.query_project_name == project_query).order_by(ResearchRun.created_at.desc()).first()
        if latest_run:
            run_id = latest_run.id

    # 3. Data Quality Validation API
    val_payload = {"project_name": project_query}
    if run_id:
        val_payload = {"research_run_id": run_id}
    val_res = client.post("/api/v1/research/validate", json=val_payload, headers=headers)
    quality_report = val_res.json() if val_res.status_code == 200 else None

    # 4. Entity Resolution API
    entity_resolution = None
    if run_id:
        res_payload = {"research_run_id": run_id}
        res_res = client.post("/api/v1/research/resolve", json=res_payload, headers=headers)
        if res_res.status_code == 200:
            entity_resolution = res_res.json()

    # 5. Fetch DB Evidences & Sources metadata
    field_evidences_list = []
    sources_list = []
    if run_id:
        ev_models = db.query(ProjectFieldEvidence).filter(ProjectFieldEvidence.research_run_id == run_id).all()
        field_evidences_list = [
            {
                "field_name": ev.field_name,
                "extracted_value": ev.extracted_value,
                "verification_status": ev.verification_status,
                "confidence": ev.confidence,
                "evidence_snippet": ev.evidence_snippet,
                "source_url": ev.source.source_url if ev.source else None,
                "retrieved_at": ev.retrieved_at.isoformat() if ev.retrieved_at else None
            }
            for ev in ev_models
        ]
        src_models = db.query(ProjectResearchSource).filter(ProjectResearchSource.research_run_id == run_id).all()
        sources_list = [
            {
                "source_name": src.source_name,
                "source_url": src.source_url,
                "source_type": src.source_type,
                "authority_level": src.authority_level,
                "retrieved_at": src.retrieved_at.isoformat() if src.retrieved_at else None
            }
            for src in src_models
        ]

    # 6. Perform Anti-Hallucination & Verification Checks
    anti_hallucination_passed = True
    hallucination_errors = []

    # Check: Non-null fields must have evidence and source URL
    if isinstance(research_data, dict):
        for field, details in research_data.items():
            if isinstance(details, dict) and details.get("value") is not None:
                v_status = details.get("verification_status")
                s_url = details.get("source_url")
                if not s_url:
                    anti_hallucination_passed = False
                    hallucination_errors.append(f"Field '{field}' has non-null value but missing source_url")
                if v_status not in ("VERIFIED", "PARTIALLY_VERIFIED", "CONFLICTING"):
                    anti_hallucination_passed = False
                    hallucination_errors.append(f"Field '{field}' has value but invalid verification_status '{v_status}'")

    # Anti-hallucination check for nonexistent project
    if case_num == 4:
        p_name = research_data.get("project_name", {}).get("value") if isinstance(research_data.get("project_name"), dict) else None
        cost_val = research_data.get("cost_inr", {}).get("value") if isinstance(research_data.get("cost_inr"), dict) else None
        tender_val = research_data.get("tender_id", {}).get("value") if isinstance(research_data.get("tender_id"), dict) else None
        contractor_val = research_data.get("contractor_name", {}).get("value") if isinstance(research_data.get("contractor_name"), dict) else None
        
        if cost_val is not None or tender_val is not None or contractor_val is not None:
            anti_hallucination_passed = False
            hallucination_errors.append("Nonexistent project test returned fabricated factual values (cost/tender/contractor)")

    test_passed = anti_hallucination_passed and (res.status_code == 200)

    # Compile Complete Response Output
    full_output = {
        "test_metadata": {
            "test_case_number": case_num,
            "query_project_name": project_query,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "execution_duration_seconds": round(duration_s, 2),
            "test_status": "PASSED" if test_passed else "FAILED",
            "anti_hallucination_passed": anti_hallucination_passed,
            "hallucination_validation_errors": hallucination_errors
        },
        "api_research_result": research_data,
        "field_evidences": field_evidences_list,
        "sources_retrieved": sources_list,
        "data_quality_report": quality_report,
        "entity_resolution": entity_resolution
    }

    # Write Complete JSON Output file
    out_file_path = os.path.join(OUTPUT_DIR, file_name)
    with open(out_file_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2, ensure_ascii=False)

    print(f"Saved complete JSON response to: {out_file_path}")
    print(f"Test Status: {'PASSED' if test_passed else 'FAILED'}")
    if quality_report:
        print(f"Quality Score: {quality_report.get('overall_quality_score')} | Class: {quality_report.get('quality_class')} | Merge Eligible: {quality_report.get('merge_eligible')}")
    
    return {
        "test_case": project_query,
        "result_file": file_name,
        "status": "PASSED" if test_passed else "FAILED",
        "research_status": research_data.get("status", "COMPLETED") if isinstance(research_data, dict) else "COMPLETED",
        "quality_class": quality_report.get("quality_class") if quality_report else "UNKNOWN",
        "overall_quality_score": quality_report.get("overall_quality_score") if quality_report else 0.0,
        "merge_eligible": quality_report.get("merge_eligible", False) if quality_report else False,
        "anti_hallucination_passed": anti_hallucination_passed
    }

def main():
    from backend.models.base import Base
    from backend.database.connection import engine
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        headers = get_auth_headers(db)
        initial_counts = count_canonical_rows(db)

        start_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Select existing canonical project for Test Case 3
        canonical_prj = db.query(Project).first()
        existing_canonical_query = canonical_prj.project_name if canonical_prj else "Construction of Flyover at Bahadurpura X Road"

        test_cases = [
            (1, "01_uppal_elevated_corridor.json", "Uppal Elevated Corridor"),
            (2, "02_iit_hyderabad_infrastructure.json", "IIT Hyderabad campus infrastructure"),
            (3, "03_existing_canonical_project.json", existing_canonical_query),
            (4, "04_nonexistent_project.json", "XYZ_Fake_Nonexistent_Bridge_Project_99999_TG")
        ]

        summary_results = []
        for case_num, file_name, query in test_cases:
            res_summary = run_acceptance_test_case(case_num, file_name, query, db, headers)
            summary_results.append(res_summary)

        completed_timestamp = datetime.now(timezone.utc).isoformat()

        post_counts = count_canonical_rows(db)
        canonical_mutations = 0
        mutation_details = {}
        for k, v in initial_counts.items():
            diff = post_counts[k] - v
            if diff != 0:
                canonical_mutations += abs(diff)
                mutation_details[k] = diff

        tests_passed = sum(1 for r in summary_results if r["status"] == "PASSED")
        tests_failed = sum(1 for r in summary_results if r["status"] != "PASSED")
        hallucination_failures = sum(1 for r in summary_results if not r["anti_hallucination_passed"])

        master_summary = {
            "test_run": {
                "started_at": start_timestamp,
                "completed_at": completed_timestamp,
                "api_version": "1.0.0",
                "environment": "LOCAL"
            },
            "canonical_db_safety": {
                "initial_counts": initial_counts,
                "post_counts": post_counts,
                "canonical_mutations": canonical_mutations,
                "mutation_details": mutation_details
            },
            "tests": summary_results,
            "summary": {
                "tests_run": len(summary_results),
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "hallucination_failures": hallucination_failures,
                "canonical_mutations": canonical_mutations
            }
        }

        master_file_path = os.path.join(OUTPUT_DIR, "all_test_results.json")
        with open(master_file_path, "w", encoding="utf-8") as f:
            json.dump(master_summary, f, indent=2, ensure_ascii=False)

        print(f"\n==================================================")
        print(f"MASTER ACCEPTANCE TEST SUMMARY")
        print(f"==================================================")
        print(f"Master file saved to: {master_file_path}")
        print(f"Tests Run: {len(summary_results)} | Passed: {tests_passed} | Failed: {tests_failed}")
        print(f"Hallucination Failures: {hallucination_failures}")
        print(f"Canonical DB Mutations: {canonical_mutations}")

    finally:
        db.close()

if __name__ == "__main__":
    main()

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

if "DATABASE_URL" not in os.environ or "postgresql" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite:///./telangana_road_intel.db"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.connection import SessionLocal, engine
from backend.models.base import Base
from backend.models.project import Project, ProjectContractor, ProjectTender, ProjectAuthority
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.models.authority import Authority
from backend.models.research import ResearchRun, ProjectResearchSource, ProjectFieldEvidence
from backend.models.data_quality import ResearchQualityReportModel, ResearchQualityIssueModel
from backend.auth.models import UserModel
from backend.auth.schemas import UserRole
from backend.auth.service import AuthService

client = TestClient(app)
ARTIFACTS_DIR = "artifacts/research_reports"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def get_auth_headers(db: Session) -> Dict[str, str]:
    admin = db.query(UserModel).filter(UserModel.role == UserRole.ADMIN.value).first()
    if not admin:
        admin = UserModel(
            username="task8_admin",
            email="task8_admin@telangana.gov.in",
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

def validate_generated_json_report(filepath: str, is_fake: bool = False) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    checks = {
        "valid_json_syntax": True,
        "has_research_run_id": "research_run_id" in data and data["research_run_id"] is not None,
        "has_project_query": "project_name_query" in data,
        "has_project_data": "project" in data and isinstance(data["project"], dict),
        "has_sources": "sources" in data and isinstance(data["sources"], list),
        "has_evidence": "evidence" in data and isinstance(data["evidence"], list),
        "has_candidate_values": "candidate_values" in data and isinstance(data["candidate_values"], list),
        "has_verification": "verification" in data and isinstance(data["verification"], dict),
        "has_conflicts": "conflicts" in data and isinstance(data["conflicts"], list),
        "has_quality_report": "quality_report" in data and isinstance(data["quality_report"], dict),
        "has_research_metadata": "research_metadata" in data and isinstance(data["research_metadata"], dict),
        "fake_no_hallucination": True
    }

    if is_fake:
        prj = data.get("project", {})
        cost = prj.get("estimated_cost", {}).get("value")
        tender = prj.get("tender_id", {}).get("value")
        contractor = prj.get("contractor", {}).get("value")
        if cost is not None or tender is not None or contractor is not None:
            checks["fake_no_hallucination"] = False

    all_passed = all(checks.values())
    return {"passed": all_passed, "checks": checks}

def run_task8_pipeline():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        headers = get_auth_headers(db)
        initial_counts = count_canonical_rows(db)

        canonical_prj = db.query(Project).first()
        third_project_name = canonical_prj.project_name if canonical_prj else "Construction of Flyover at Bahadurpura X Road"

        test_cases = [
            ("uppal_elevated_corridor.json", "Uppal Elevated Corridor", False),
            ("iit_hyderabad_infrastructure.json", "IIT Hyderabad campus infrastructure", False),
            ("third_real_project.json", third_project_name, False),
            ("fake_project.json", "XYZ_Fake_Nonexistent_Bridge_Project_99999_TG", True)
        ]

        results_summary = []

        for filename, query, is_fake in test_cases:
            print(f"\n--------------------------------------------------")
            print(f"Task 8 Research Execution: '{query}' -> {filename}")
            print(f"--------------------------------------------------")

            # 1. POST /api/v1/research/project
            start_time = time.time()
            post_res = client.post("/api/v1/research/project", json={"project_name": query, "force_refresh": True}, headers=headers)
            assert post_res.status_code == 200, f"POST /api/v1/research/project failed ({post_res.status_code}): {post_res.text}"
            res_data = post_res.json()
            duration = round(time.time() - start_time, 2)

            run_id = None
            if res_data.get("project_id") and str(res_data.get("project_id")).isdigit():
                run_id = int(res_data.get("project_id"))
            else:
                latest = db.query(ResearchRun).filter(ResearchRun.query_project_name == query).order_by(ResearchRun.created_at.desc()).first()
                if latest:
                    run_id = latest.id

            assert run_id is not None, f"Could not determine research_run_id for '{query}'"

            # 2. Trigger data quality validation API so quality report model is stored
            val_res = client.post("/api/v1/research/validate", json={"research_run_id": run_id}, headers=headers)
            quality_data = val_res.json() if val_res.status_code == 200 else {}

            # 3. GET /api/v1/research/{research_run_id}/json (Download JSON Report)
            get_json_res = client.get(f"/api/v1/research/{run_id}/json", headers=headers)
            assert get_json_res.status_code == 200, f"GET /api/v1/research/{run_id}/json failed: {get_json_res.text}"
            assert get_json_res.headers.get("content-type") == "application/json"

            json_report = get_json_res.json()

            # 4. Save actual JSON file to artifacts/research_reports/{filename}
            filepath = os.path.join(ARTIFACTS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(json_report, f, indent=2, ensure_ascii=False)

            print(f"Downloaded and saved artifact JSON report to: {filepath}")

            # 5. Programmatic Validation
            val_result = validate_generated_json_report(filepath, is_fake=is_fake)
            print(f"JSON Validation Passed: {val_result['passed']}")

            # Statistics
            prj_fields = json_report.get("project", {})
            populated_fields = sum(1 for k, v in prj_fields.items() if isinstance(v, dict) and v.get("value") is not None)
            not_found_fields = sum(1 for k, v in prj_fields.items() if isinstance(v, dict) and (v.get("value") is None or v.get("verification_status") == "NOT_FOUND"))
            sources_searched = json_report.get("research_metadata", {}).get("sources_checked", 0)
            sources_retrieved = len(json_report.get("sources", []))
            conflicts_count = len(json_report.get("conflicts", []))
            quality_score = json_report.get("quality_report", {}).get("overall_quality_score", 0.0)

            results_summary.append({
                "filename": filename,
                "query": query,
                "research_run_id": run_id,
                "duration_seconds": duration,
                "populated_fields": populated_fields,
                "not_found_fields": not_found_fields,
                "sources_searched": sources_searched,
                "sources_retrieved": sources_retrieved,
                "conflicts_count": conflicts_count,
                "quality_score": quality_score,
                "validation_passed": val_result["passed"]
            })

        post_counts = count_canonical_rows(db)
        canonical_mutations = sum(abs(post_counts[k] - initial_counts[k]) for k in initial_counts)

        print("\n==================================================")
        print("TASK 8 PIPELINE SUMMARY")
        print("==================================================")
        print(f"Canonical DB Mutations: {canonical_mutations}")
        for r in results_summary:
            print(f"- File: {r['filename']} | Query: {r['query']} | Run ID: {r['research_run_id']} | Populated: {r['populated_fields']} | NOT_FOUND: {r['not_found_fields']} | Quality Score: {r['quality_score']} | Validation: {r['validation_passed']}")

        with open("artifacts/research_reports/task8_execution_summary.json", "w", encoding="utf-8") as f:
            json.dump({"canonical_mutations": canonical_mutations, "test_cases": results_summary}, f, indent=2)

    finally:
        db.close()

if __name__ == "__main__":
    run_task8_pipeline()

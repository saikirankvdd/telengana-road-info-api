from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from backend.models.project import Project, ProjectAuthority, ProjectContractor, ProjectTender
from backend.models.road import Road
from backend.models.tender import Tender
from backend.models.contractor import Contractor

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def get_project_by_id(self, project_db_id: int) -> Project | None:
        return (
            self.db.query(Project)
            .options(
                joinedload(Project.road),
                joinedload(Project.source),
                joinedload(Project.authority_associations).joinedload(ProjectAuthority.authority),
                joinedload(Project.contractor_associations).joinedload(ProjectContractor.contractor),
                joinedload(Project.tender_associations).joinedload(ProjectTender.tender),
            )
            .filter(Project.id == project_db_id)
            .first()
        )

    def get_project_by_code(self, project_code: str) -> Project | None:
        return (
            self.db.query(Project)
            .options(
                joinedload(Project.road),
                joinedload(Project.source),
                joinedload(Project.authority_associations).joinedload(ProjectAuthority.authority),
                joinedload(Project.contractor_associations).joinedload(ProjectContractor.contractor),
                joinedload(Project.tender_associations).joinedload(ProjectTender.tender),
            )
            .filter(Project.project_id == project_code)
            .first()
        )

    def list_projects(self, skip: int = 0, limit: int = 50) -> list[Project]:
        return (
            self.db.query(Project)
            .options(
                joinedload(Project.road),
                joinedload(Project.source),
                joinedload(Project.authority_associations).joinedload(ProjectAuthority.authority),
                joinedload(Project.contractor_associations).joinedload(ProjectContractor.contractor),
                joinedload(Project.tender_associations).joinedload(ProjectTender.tender),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_projects(self, query: str) -> list[dict]:
        """
        Deterministic, database-driven search for projects.
        Normalizes query and ranks exact/partial matches across:
        1. Project Name
        2. Road Name
        3. Tender title/description
        4. Contractor name
        """
        normalized = query.strip().lower()
        projects = (
            self.db.query(Project)
            .options(
                joinedload(Project.road),
                joinedload(Project.source),
                joinedload(Project.authority_associations).joinedload(ProjectAuthority.authority),
                joinedload(Project.contractor_associations).joinedload(ProjectContractor.contractor),
                joinedload(Project.tender_associations).joinedload(ProjectTender.tender),
            )
            .all()
        )

        results = []
        for proj in projects:
            score = 0.0
            matched_by = None

            p_name = (proj.project_name or "").lower()
            p_desc = (proj.description or "").lower()
            p_code = (proj.project_id or "").lower()

            if normalized == p_name or normalized == p_code:
                score = 1.0
                matched_by = "PROJECT_EXACT_NAME"
            elif normalized in p_name:
                score = 0.85
                matched_by = "PROJECT_NAME_PARTIAL"
            elif any(word in p_name for word in normalized.split()):
                score = 0.70
                matched_by = "PROJECT_NAME_KEYWORD"

            # Check Road Name match
            if proj.road and proj.road.road_name:
                r_name = proj.road.road_name.lower()
                if normalized in r_name:
                    if score < 0.8:
                        score = 0.80
                        matched_by = "ROAD_NAME"

            # Check Tender matches
            for t_assoc in proj.tender_associations:
                if t_assoc.tender and t_assoc.tender.title:
                    t_title = t_assoc.tender.title.lower()
                    if normalized in t_title:
                        if score < 0.75:
                            score = 0.75
                            matched_by = "TENDER_TITLE"

            # Check Contractor matches
            for c_assoc in proj.contractor_associations:
                c_name_val = getattr(c_assoc.contractor, "legal_name", None) or getattr(c_assoc.contractor, "name", None)
                if c_assoc.contractor and c_name_val:
                    c_name = c_name_val.lower()
                    if normalized in c_name:
                        if score < 0.75:
                            score = 0.75
                            matched_by = "CONTRACTOR_NAME"

            if score > 0:
                results.append({
                    "project": proj,
                    "confidence_score": round(score, 2),
                    "matched_by": matched_by
                })

        # Sort by confidence score descending
        results.sort(key=lambda x: x["confidence_score"], reverse=True)
        return results

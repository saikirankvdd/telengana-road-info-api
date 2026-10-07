-- Initial Database Schema Migration for Telangana Road & Project Intelligence API
-- Supports PostgreSQL + PostGIS

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    base_url TEXT,
    official BOOLEAN DEFAULT FALSE,
    description TEXT,
    authentication_type VARCHAR(100) DEFAULT 'PUBLIC',
    active BOOLEAN DEFAULT TRUE,
    source_url TEXT,
    source_record_id TEXT,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_records (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    external_record_id TEXT,
    external_url TEXT,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    checksum VARCHAR(128),
    raw_payload_reference TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS authorities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT,
    authority_type VARCHAR(100),
    parent_authority_id INTEGER REFERENCES authorities(id) ON DELETE SET NULL,
    state VARCHAR(100) DEFAULT 'Telangana',
    district VARCHAR(100),
    official_website TEXT,
    official_email VARCHAR(255),
    official_phone VARCHAR(100),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(100),
    official_url TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contractors (
    id SERIAL PRIMARY KEY,
    legal_name TEXT NOT NULL,
    normalized_name TEXT,
    registration_number VARCHAR(100),
    contractor_type VARCHAR(100),
    address TEXT,
    email VARCHAR(255),
    phone VARCHAR(100),
    website TEXT,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roads (
    id SERIAL PRIMARY KEY,
    road_name VARCHAR(255) NOT NULL,
    normalized_road_name VARCHAR(255),
    road_number VARCHAR(100),
    road_type VARCHAR(100),
    authority_id INTEGER REFERENCES authorities(id),
    geometry GEOMETRY(Geometry, 4326),
    geometry_wkt TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    length_km DOUBLE PRECISION,
    source_id INTEGER REFERENCES sources(id),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_name TEXT NOT NULL,
    normalized_project_name TEXT,
    description TEXT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    road_id INTEGER REFERENCES roads(id),
    authority_id INTEGER REFERENCES authorities(id),
    start_location TEXT,
    end_location TEXT,
    length_km DOUBLE PRECISION,
    estimated_cost DOUBLE PRECISION,
    awarded_cost DOUBLE PRECISION,
    appointed_date TIMESTAMP,
    start_date TIMESTAMP,
    expected_completion_date TIMESTAMP,
    actual_completion_date TIMESTAMP,
    status VARCHAR(100),
    physical_progress DOUBLE PRECISION,
    execution_mode VARCHAR(100),
    geometry GEOMETRY(Geometry, 4326),
    geometry_wkt TEXT,
    source_id INTEGER REFERENCES sources(id),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_locations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    state VARCHAR(100) DEFAULT 'Telangana',
    district VARCHAR(100),
    municipality VARCHAR(100),
    city VARCHAR(100),
    locality VARCHAR(100),
    address_text TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geometry GEOMETRY(Geometry, 4326),
    geometry_wkt TEXT,
    location_source_id INTEGER REFERENCES sources(id),
    confidence_score DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_roads (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    road_id INTEGER NOT NULL REFERENCES roads(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) DEFAULT 'PROJECT_ON_ROAD'
);

CREATE TABLE IF NOT EXISTS project_authorities (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    authority_id INTEGER NOT NULL REFERENCES authorities(id) ON DELETE CASCADE,
    role VARCHAR(100) DEFAULT 'PRIMARY_AUTHORITY'
);

CREATE TABLE IF NOT EXISTS project_contractors (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    contractor_id INTEGER NOT NULL REFERENCES contractors(id) ON DELETE CASCADE,
    role VARCHAR(100) DEFAULT 'MAIN_CONTRACTOR',
    award_date TIMESTAMP,
    contract_value DOUBLE PRECISION,
    source_id INTEGER REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    tender_id TEXT NOT NULL,
    tender_reference_number TEXT,
    title TEXT NOT NULL,
    description TEXT,
    organisation TEXT,
    department TEXT,
    published_date TIMESTAMP,
    closing_date TIMESTAMP,
    estimated_value DOUBLE PRECISION,
    awarded_value DOUBLE PRECISION,
    status VARCHAR(100),
    source_url TEXT,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_tenders (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tender_id INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    tender_id INTEGER REFERENCES tenders(id) ON DELETE SET NULL,
    contractor_id INTEGER REFERENCES contractors(id) ON DELETE SET NULL,
    contract_reference TEXT,
    contract_value DOUBLE PRECISION,
    award_date TIMESTAMP,
    appointed_date TIMESTAMP,
    completion_period_days INTEGER,
    completion_date TIMESTAMP,
    contract_status VARCHAR(100) DEFAULT 'AWARDED',
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_status_history (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(100) NOT NULL,
    progress_percentage DOUBLE PRECISION,
    effective_date TIMESTAMP,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_cost_history (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cost_type VARCHAR(100) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    effective_date TIMESTAMP,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_identifiers (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    identifier_type VARCHAR(100) NOT NULL,
    identifier_value VARCHAR(255) NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS government_orders (
    id SERIAL PRIMARY KEY,
    go_number VARCHAR(255) NOT NULL,
    issue_date TIMESTAMP,
    title TEXT NOT NULL,
    description TEXT,
    department VARCHAR(255),
    document_url TEXT,
    source_id INTEGER REFERENCES sources(id),
    source_record_id INTEGER REFERENCES source_records(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS government_order_projects (
    id SERIAL PRIMARY KEY,
    government_order_id INTEGER NOT NULL REFERENCES government_orders(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes for performance & query optimization
CREATE INDEX IF NOT EXISTS idx_projects_project_id ON projects(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);
CREATE INDEX IF NOT EXISTS idx_projects_norm_name ON projects(normalized_project_name);
CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

CREATE INDEX IF NOT EXISTS idx_tenders_tender_id ON tenders(tender_id);
CREATE INDEX IF NOT EXISTS idx_tenders_ref_no ON tenders(tender_reference_number);

CREATE INDEX IF NOT EXISTS idx_contractors_legal_name ON contractors(legal_name);
CREATE INDEX IF NOT EXISTS idx_contractors_norm_name ON contractors(normalized_name);

CREATE INDEX IF NOT EXISTS idx_authorities_name ON authorities(name);
CREATE INDEX IF NOT EXISTS idx_authorities_norm_name ON authorities(normalized_name);

CREATE INDEX IF NOT EXISTS idx_locations_district ON project_locations(district);
CREATE INDEX IF NOT EXISTS idx_locations_municipality ON project_locations(municipality);
CREATE INDEX IF NOT EXISTS idx_locations_city ON project_locations(city);

-- Spatial PostGIS GIST Indexes
CREATE INDEX IF NOT EXISTS idx_roads_geometry ON roads USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_projects_geometry ON projects USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_project_locations_geometry ON project_locations USING GIST (geometry);


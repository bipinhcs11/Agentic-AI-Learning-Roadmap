CREATE TABLE IF NOT EXISTS demo_catalog (
  tenant VARCHAR(40) NOT NULL,
  document_id VARCHAR(80) NOT NULL,
  summary VARCHAR(500) NOT NULL,
  PRIMARY KEY (tenant, document_id)
);

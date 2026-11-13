BEGIN;
CREATE TABLE IF NOT EXISTS purchase_imports (
	id UUID NOT NULL, 
	document_id VARCHAR(200) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	result JSON NOT NULL, 
	imported_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_purchase_imports_document_id UNIQUE (document_id)
);
COMMIT;

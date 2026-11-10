-- Run once against an existing PostgreSQL database before starting this version.
BEGIN;
ALTER TABLE users ADD COLUMN reader_card BIGINT;
ALTER TABLE users ADD CONSTRAINT uq_users_reader_card UNIQUE (reader_card);
DO $$
DECLARE
    reader RECORD;
    violated_constraint TEXT;
BEGIN
    FOR reader IN SELECT id FROM users WHERE role = 'reader' AND reader_card IS NULL LOOP
        LOOP
            BEGIN
                UPDATE users SET reader_card = floor(random() * 9000000000 + 1000000000)::bigint
                WHERE id = reader.id;
                EXIT;
            EXCEPTION WHEN unique_violation THEN
                GET STACKED DIAGNOSTICS violated_constraint = CONSTRAINT_NAME;
                IF violated_constraint <> 'uq_users_reader_card' THEN RAISE; END IF;
            END;
        END LOOP;
    END LOOP;
END $$;

CREATE TABLE books (
	id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	author VARCHAR(300) NOT NULL, 
	publication_year INTEGER NOT NULL, 
	publisher VARCHAR(300) NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE book_copies (
	id UUID NOT NULL, 
	book_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(book_id) REFERENCES books (id)
)

;
CREATE INDEX ix_book_copies_book_id ON book_copies (book_id);

CREATE TABLE loans (
	id UUID NOT NULL, 
	copy_id UUID NOT NULL, 
	reader_id UUID NOT NULL, 
	librarian_id UUID NOT NULL, 
	issued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	due_date DATE NOT NULL, 
	returned_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_loans_due_date CHECK (due_date >= CAST(issued_at AS DATE)), 
	CONSTRAINT ck_loans_returned_at CHECK (returned_at IS NULL OR returned_at >= issued_at), 
	FOREIGN KEY(copy_id) REFERENCES book_copies (id), 
	FOREIGN KEY(reader_id) REFERENCES users (id), 
	FOREIGN KEY(librarian_id) REFERENCES users (id)
)

;
CREATE INDEX ix_loans_copy_id ON loans (copy_id);
CREATE INDEX ix_loans_librarian_id ON loans (librarian_id);
CREATE INDEX ix_loans_reader_id ON loans (reader_id);
CREATE UNIQUE INDEX uq_loans_active_copy ON loans (copy_id) WHERE returned_at IS NULL;
COMMIT;

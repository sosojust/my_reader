-- Add metadata columns to books table
ALTER TABLE books ADD COLUMN author VARCHAR(255) NULL;
ALTER TABLE books ADD COLUMN publisher VARCHAR(255) NULL;
ALTER TABLE books ADD COLUMN published_date VARCHAR(50) NULL;
ALTER TABLE books ADD COLUMN description TEXT NULL;
ALTER TABLE books ADD COLUMN language VARCHAR(10) NULL;
ALTER TABLE books ADD COLUMN sections_count INT DEFAULT 0;

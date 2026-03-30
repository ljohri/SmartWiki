-- Audit log for document submissions (separate from Wiki.js tables; same DB for simplicity)
CREATE TABLE IF NOT EXISTS submissions_log (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL DEFAULT 'unknown',
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  tags TEXT[],
  original_filename TEXT NOT NULL,
  target_path TEXT,
  ai_decision JSONB,
  status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS submissions_log_created_at_idx ON submissions_log (created_at DESC);
CREATE INDEX IF NOT EXISTS submissions_log_status_idx ON submissions_log (status);

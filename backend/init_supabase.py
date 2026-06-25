"""
Run this once to create Supabase tables.
Usage: python init_supabase.py
"""
import sys
sys.path.insert(0, ".")

from supabase import create_client
from app.config import get_settings

s = get_settings()
sb = create_client(s.supabase_url, s.supabase_service_key)

sql = open("app/db/supabase_schema.sql").read()

# Split by semicolons and execute each statement
statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
for stmt in statements:
    if stmt.upper().startswith("--"):
        continue
    try:
        sb.table("_sql").insert({"sql": stmt}).execute()
    except Exception:
        pass  # Expected - _sql table doesn't exist, try raw query

# Use the mgmt API to run SQL
print("Attempting to run schema via Supabase...")
try:
    resp = sb.rpc("exec", {"query": sql})
    print("Schema executed via RPC")
except:
    print("RPC not available. Run the SQL manually in Supabase SQL Editor.")
    print(f"SQL file: app/db/supabase_schema.sql")
    print(f"Supabase URL: {s.supabase_url}")

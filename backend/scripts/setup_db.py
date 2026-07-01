import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def parse_db_url():
    """Parse DATABASE_URL from .env to extract connection parameters."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    
    env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    v = v.strip()
                    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                        v = v[1:-1]
                    if ' #' in v:
                        v = v.split(' #', 1)[0].strip()
                    env[k.strip()] = v
                    
    db_url = env.get("DATABASE_URL", "")
    
    # Parse: postgresql://user:password@host:port/dbname
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if match:
        return {
            "user": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "dbname": match.group(5),
        }
    return None


def create_database_if_not_exists():
    """Create the dftpc_db database if it doesn't exist using raw psycopg2."""
    import psycopg2
    
    params = parse_db_url()
    if not params:
        print("Could not parse DATABASE_URL from .env, skipping DB creation.")
        return
    
    db_name = params["dbname"]
    print(f"Checking if database '{db_name}' exists...")
    
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=params["user"],
            password=params["password"],
            host=params["host"],
            port=params["port"],
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;",
            (db_name,),
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"Database '{db_name}' does not exist. Creating it...")
            cursor.execute(f'CREATE DATABASE "{db_name}";')
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        raise


def setup_db():
    print("==================================================")
    print("STARTING DATABASE SETUP & DATA IMPORT PIPELINE")
    print("==================================================")

    # 0. Create the database BEFORE importing any SQLAlchemy modules
    create_database_if_not_exists()

    # --- Deferred imports (these trigger engine creation) ---
    from app.database import init_db, drop_db
    from scripts.import_tag_mapping_csv import import_tag_mapping
    from scripts.import_dcs_data import import_dcs_data
    from scripts.import_analysis_csv import import_analysis
    from scripts.seed_users import seed_users
    from scripts.run_daily_kpi import run_daily_kpi

    # 1. Drop and initialize database schema
    print("\n1. Dropping existing tables...")
    try:
        drop_db()
    except Exception as e:
        print(f"Drop DB warning: {e}")

    print("\n2. Initializing new database tables...")
    init_db()

    # 2. Import Tag Mappings
    print("\n3. Importing tag mappings from CSV...")
    import_tag_mapping()

    # 3. Import DCS Process Data
    print("\n4. Importing DCS data from Excel...")
    import_dcs_data()

    # 4. Import Lab Analysis CSV
    print("\n5. Importing lab analysis from CSV...")
    import_analysis()

    # 5. Seed Users
    print("\n6. Seeding default users (admin & engineer)...")
    seed_users()

    # 6. Pre-calculate Daily KPIs
    print("\n7. Pre-calculating daily KPIs for all imported dates...")
    run_daily_kpi()

    print("\n==================================================")
    print("DATABASE SETUP COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    setup_db()

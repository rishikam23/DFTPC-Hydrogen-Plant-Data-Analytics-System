import os
import sys
import pandas as pd
from sqlalchemy import create_engine

# Add backend to path so we can run this script directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base
from app.models import LabAnalysis
from config import settings

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "analysis_data_jan1_20_FINAL.csv")

engine = create_engine(settings.DATABASE_URL)

TAG_MAP = {
    "927QR111": ("SalesGas", "N2"),
    "927QR112": ("SalesGas", "CH4"),
    "927QR113": ("SalesGas", "CO2"),
    "927QR114": ("SalesGas", "C2"),
    "927QR115": ("SalesGas", "C3"),
    "927QR116": ("SalesGas", "iC4"),
    "927QR117": ("SalesGas", "nC4"),
    "927QR118": ("SalesGas", "C5"),
    "60QR111": ("Reformer", "CH4"),
    "61QIA011TX": ("HPSA", "N2"),
    "61QIA012TX": ("HPSA", "CO"),
    "61QIA013TX": ("HPSA", "CH4"),
    "61QIA010AI": ("HPSA", "H2"),
}


def import_analysis():
    print("Importing analysis CSV...")

    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    tag_col = df.columns[0]
    date_cols = df.columns[1:]

    print(f"Detected {len(date_cols)} analysis dates")

    df_long = df.melt(
        id_vars=[tag_col],
        value_vars=date_cols,
        var_name="analysis_date",
        value_name="value"
    )

    df_long["analysis_date"] = pd.to_datetime(df_long["analysis_date"], errors="coerce")
    df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")

    df_long = df_long.dropna(subset=["analysis_date", "value"])

    records = []

    for _, row in df_long.iterrows():
        raw_tag = str(row[tag_col]).strip()
        
        # Determine sample point and component
        sample_point, component = TAG_MAP.get(raw_tag, (None, None))
        
        if not sample_point:
            if raw_tag.startswith("analysis_"):
                parts = raw_tag.split("_")
                if len(parts) >= 3:
                    # Clean sample point and component names
                    sample_point = parts[1].upper()
                    component = parts[-1].upper()
                    
                    if "sales" in raw_tag.lower():
                        sample_point = "SalesGas"
                    elif "reformer" in raw_tag.lower():
                        sample_point = "Reformer"
                    elif "leansulfinol" in raw_tag.lower():
                        sample_point = "LeanSulfinol"
                    elif "co2" in raw_tag.lower() and "export" in raw_tag.lower():
                        sample_point = "CO2Export"
                else:
                    sample_point = "CSV_IMPORT"
                    component = raw_tag
            else:
                sample_point = "CSV_IMPORT"
                component = raw_tag

        records.append({
            "analysis_date": row["analysis_date"],
            "tag_name": raw_tag,
            "sample_point": sample_point,
            "component": component,
            "value_mol_percent": float(row["value"])
        })

    if not records:
        print("No analysis records to import")
        return

    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(LabAnalysis.__table__.delete())
        conn.execute(LabAnalysis.__table__.insert(), records)

    print(f"Imported {len(records)} lab analysis rows successfully")


if __name__ == "__main__":
    import_analysis()

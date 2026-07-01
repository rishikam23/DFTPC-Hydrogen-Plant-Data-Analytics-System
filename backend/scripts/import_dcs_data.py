import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path so we can run this script directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base
from app.models import ProcessData, ProcessTag
from config import settings

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "SASREF Data October - 2025 V2.0.xlsx")

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def import_dcs_data():
    print("Reading DCS Data sheet...")

    # ===============================
    # 1. Read full sheet
    # ===============================
    df = pd.read_excel(
        EXCEL_PATH,
        sheet_name="DCS Data",
        header=None
    )

    # ===============================
    # FIXED positions (from your file)
    # ===============================
    TAG_COLUMN = 0          # column A
    DESC_COLUMN = 1         # column B
    UNIT_COLUMN = 2         # column C
    DATA_START_COL = 4      # column E
    DATA_START_ROW = 5      # numeric values start

    # ===============================
    # 2. Extract dates
    # ===============================
    date_headers = df.iloc[1, DATA_START_COL:]
    dates = pd.to_datetime(date_headers, errors="coerce")

    valid_dates = dates.dropna()
    print(f"Detected {len(valid_dates)} dates")

    # ===============================
    # 3. Extract tag names
    # ===============================
    matched_tags = (
        df.iloc[DATA_START_ROW:, TAG_COLUMN]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    print(f"Detected {len(matched_tags)} tags")

    # ===============================
    # 4. Build records
    # ===============================
    records = []

    # Map tags and descriptions to insert into ProcessTag table
    db = SessionLocal()
    try:
        # Clear existing tags to prevent duplicates
        db.query(ProcessTag).delete()
        
        seen_tags = set()
        for idx in range(4, df.shape[0]):
            tag = df.iloc[idx, TAG_COLUMN]
            desc = df.iloc[idx, DESC_COLUMN]
            unit = df.iloc[idx, UNIT_COLUMN]
            if pd.isna(tag) or str(tag).strip() == "":
                continue
            tag_str = str(tag).strip()
            if tag_str not in seen_tags:
                seen_tags.add(tag_str)
                db_tag = ProcessTag(
                    tag_name=tag_str,
                    parameter=str(desc).strip() if not pd.isna(desc) else "",
                    uom=str(unit).strip() if not pd.isna(unit) else ""
                )
                db.add(db_tag)
        
        # Add simulated electricity tag mapping
        if "Electricity_Excl_K6006" not in seen_tags:
            db_tag = ProcessTag(
                tag_name="Electricity_Excl_K6006",
                parameter="Electricity excluding K-6006",
                uom="MWh"
            )
            db.add(db_tag)
        db.commit()
        print("Populated ProcessTag table with mappings successfully")
    except Exception as e:
        db.rollback()
        print(f"Error populating ProcessTag table: {e}")
    finally:
        db.close()

    # Process DCS data records
    for row_offset, tag in enumerate(matched_tags):
        excel_row = DATA_START_ROW + row_offset

        for col_idx, timestamp in enumerate(dates):
            if pd.isna(timestamp):
                continue

            value = df.iloc[excel_row, DATA_START_COL + col_idx]

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            records.append({
                "timestamp": timestamp,
                "tag_name": tag,
                "tag_value": value,
                "data_quality": "GOOD",
            })

    # Add simulated electricity process data records
    for timestamp in dates:
        if pd.isna(timestamp):
            continue
        records.append({
            "timestamp": timestamp,
            "tag_name": "Electricity_Excl_K6006",
            "tag_value": (11.5 + 7.33) * 24, # 451.92 MWh
            "data_quality": "GOOD",
        })

    if not records:
        print("No records generated")
        return

    # ===============================
    # 5. Insert into DB
    # ===============================
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(ProcessData.__table__.delete())
        conn.execute(ProcessData.__table__.insert(), records)

    print(f"Imported {len(records)} DCS data points successfully")


if __name__ == "__main__":
    import_dcs_data()
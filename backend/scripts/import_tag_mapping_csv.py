import os
import sys
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

# Add backend to path so we can run this script directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import TagMapping
from app.database import engine

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "operational_data_jan1_20_FINAL.csv")


def import_tag_mapping():
    print("Importing tag mapping CSV...")

    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at {CSV_PATH}")
        return

    # read csv
    df = pd.read_csv(CSV_PATH)

    records = []

    for _, row in df.iterrows():
        tag = str(row.iloc[0]).strip()

        # skip empty / nan
        if not tag or tag.lower() == "nan":
            continue

        records.append({
            "tag_name": tag,
            "source_tag": tag,
            "is_calculated": False
        })

    if not records:
        print("No tags found.")
        return

    stmt = insert(TagMapping).values(records)

    stmt = stmt.on_conflict_do_nothing(
        index_elements=["tag_name"]
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"Imported {len(records)} tags safely.")


if __name__ == "__main__":
    import_tag_mapping()
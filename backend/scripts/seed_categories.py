"""Idempotently loads db/seed_data/categories.json into the categories table.

Run with: poetry run python -m scripts.seed_categories
(run as a module, from backend/, so the `db`/`models` packages resolve)
Safe to re-run: upserts by developer_slug rather than inserting duplicates.
"""
import json
import os

from db.session import SessionLocal
from models.category import Category

SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "db", "seed_data", "categories.json")


def seed_categories() -> None:
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        categories = json.load(f)

    db = SessionLocal()
    try:
        created, updated = 0, 0
        for entry in categories:
            existing = (
                db.query(Category)
                .filter(Category.developer_slug == entry["developer_slug"])
                .first()
            )
            if existing:
                existing.classification = entry["classification"]
                existing.category_name = entry["category_name"]
                existing.description = entry.get("description")
                existing.tax_treatment = entry.get("tax_treatment")
                existing.asset_class = entry.get("asset_class")
                updated += 1
            else:
                db.add(Category(
                    classification=entry["classification"],
                    category_name=entry["category_name"],
                    developer_slug=entry["developer_slug"],
                    description=entry.get("description"),
                    tax_treatment=entry.get("tax_treatment"),
                    asset_class=entry.get("asset_class"),
                ))
                created += 1
        db.commit()
        print(f"Seeded categories: {created} created, {updated} updated.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()

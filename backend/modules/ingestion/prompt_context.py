"""Builds the two free-text blocks `categorize_transactions` needs (predefined
categories and the user's custom rules) from the actual database state, so the
categorization prompt always reflects what's really in `categories`/`custom_rules`
rather than a hardcoded copy.
"""
from sqlalchemy.orm import Session

from models.category import Category
from models.custom_rule import CustomRule


def build_predefined_categories_text(db: Session) -> str:
    categories = db.query(Category).all()
    return "\n".join(
        f"- developer_slug: {c.developer_slug} ({c.category_name})" for c in categories
    )


def build_custom_rules_text(db: Session, user_id) -> str:
    rules = (
        db.query(CustomRule)
        .filter(CustomRule.user_id == user_id, CustomRule.is_active.is_(True))
        .all()
    )
    if not rules:
        return "None."
    return "\n".join(
        f"{i}. If a transaction matches '{rule.keyword_pattern}', classify it as '{rule.assigned_category}'."
        for i, rule in enumerate(rules, start=1)
    )

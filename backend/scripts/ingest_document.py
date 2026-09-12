"""Ingests a source document (PDF) into the knowledge_chunks table for RAG retrieval.

Run any time you have a new or updated supporting document — this is the general
mechanism for growing the advisor's knowledge base, not a one-off seeding step.
Re-running with the same --title replaces that document's existing chunks.

Usage (from backend/, as a module so the db/models packages resolve):
    poetry run python -m scripts.ingest_document "<path-to-pdf>" --title "Nigeria Tax Act 2025"
"""
import argparse

from db.session import SessionLocal
from modules.advisory.document_ingestion import ingest_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file_path", help="Path to the PDF to ingest")
    parser.add_argument("--title", required=True, help="Source title, e.g. 'Nigeria Tax Act 2025'")
    args = parser.parse_args()

    db = SessionLocal()
    print(f"Ingesting '{args.file_path}' as '{args.title}'...")
    try:
        count = ingest_document(db, args.file_path, args.title)
        print(f"Ingested {count} chunks from '{args.title}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

# GigTax — UML Diagrams

All diagrams are written in **PlantUML** format (`.puml` files).
PlantUML generates proper, academically standard UML from plain text.

---

## Files in This Folder

| File | Diagram Type | Purpose |
|---|---|---|
| `use_case.puml` | Use Case Diagram | Actors and system interactions |
| `activity.puml` | Activity Diagram | Full tax compliance workflow |
| `class_diagram.puml` | Class Diagram | Core data model and relationships |
| `seq_statement_upload.puml` | Sequence Diagram | Bank statement upload and parse flow |
| `seq_manual_entry.puml` | Sequence Diagram | Manual income/expense entry flow |
| `seq_rag_advisory.puml` | Sequence Diagram | AI Tax Advisor (RAG pipeline) |
| `seq_report_generation.puml` | Sequence Diagram | Report generation and filing guidance |

---

## How to Edit and Export (3 Options)

### Option 1 — VS Code (Recommended for editing)

1. Install **VS Code** if not already installed
2. Install the extension: **PlantUML** by jebbs
   - Open VS Code → Extensions (Ctrl+Shift+X) → search "PlantUML" → Install
3. Also install **Java** (required by PlantUML):
   - Download from https://adoptium.net
4. Open any `.puml` file in VS Code
5. Press `Alt+D` to preview the diagram in real time
6. To export: Right-click in the preview → **Export current diagram**
   - Choose PNG or SVG for your report

### Option 2 — Online (No installation required)

1. Go to **https://www.plantuml.com/plantuml**
2. Open a `.puml` file in Notepad
3. Copy and paste the contents into the website
4. Download the generated PNG or SVG image

### Option 3 — draw.io (For drag-and-drop editing after export)

1. Export from PlantUML as SVG first (using Option 1 or 2)
2. Open **https://app.diagrams.net**
3. Import the SVG → Edit visually → Export as PNG or PDF

---

## Recommended Export Settings for Academic Report

- **Format:** PNG at 300 DPI, or SVG (vector — infinitely scalable)
- **For Word/PDF report:** Use PNG (300 DPI minimum)
- **Caption format:** Figure X.X: [Diagram Name] (Author, 2025)

---

## Relationship Key (Class Diagram)

| Symbol | Meaning |
|---|---|
| `*--` (filled diamond) | Composition — part cannot exist without whole |
| `o--` (hollow diamond) | Aggregation — "has-a" relationship |
| `-->` (solid arrow) | Association — general relationship |
| `..>` (dashed arrow) | Dependency — uses or creates |
| `<\|--` | Inheritance — is-a relationship |

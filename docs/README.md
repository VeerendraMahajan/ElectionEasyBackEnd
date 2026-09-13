# VoterLens - Documentation Index

This directory contains comprehensive, simple-English documentation for every component of the **VoterLens** platform:

1. [High-Level Design (HLD)](./hld.md): System goals, processing flow, and Mermaid architecture diagram.
2. [Architecture Overview](./architecture.md): Layered architecture, API, service boundaries, and design rules.
3. [Database Design & ER Diagram](./database.md): Normalized relational schema, Mermaid ER diagram, and ascending serial indexes.
4. [Extraction Pipeline](./extraction-pipeline.md): Step-by-step extraction workflow and data flow diagram.
5. [PDF Processing & Font Mapping](./pdf-processing.md): PyMuPDF rendering, text vs scan inspection, and deterministic font remapping (`font_mapper.py`).
6. [OCR Pipeline & Zone Processing](./ocr.md): EasyOCR integration, local zone preprocessing, allowlists, and bounding boxes.
7. [Vision AI & Hybrid Confidence Cascade](./llm-extraction.md): Selective Gemini 3.5 Flash Lite integration, prompts, cost optimization, and 429 quota resilience.
8. [Normalization & Transliteration](./normalization.md): Bilingual storage, phonetic transliteration, and ID rules.
9. [Validation & Confidence Scoring](./validation.md): Business rules, confidence calculation, and human review queue.
10. [API Reference](./api.md): REST API endpoints for upload, documents, jobs, and records with ascending serial ordering.
11. [Background Processing](./background-processing.md): Celery and Redis asynchronous worker pipeline.
12. [Deployment & Docker Operations](./deployment.md): Docker Compose setup, container restart commands, health checks, and migrations.
13. [Configuration Reference](./configuration.md): Complete list of environment variables and defaults.
14. [Testing & Verification Guide](./testing.md): Live endpoint testing, Postman collection, and verification commands.
15. [Troubleshooting Guide](./troubleshooting.md): Common error resolutions, 429 quota handling, and debugging steps.
16. [Architecture Decision Log (ADR)](./decisions.md): Record of key engineering and architectural decisions (ADR 001 to 008).

# AGENTS
# Genio Recursive Memory Engine

Genio is a recursive cognitive engine designed to ingest, interpret, reflect, visualize, and embed memory streams from diverse data sources—text, audio, video—by structuring them into semantic vectors anchored in temporal and cognitive context.

## Agent Responsibilities

Agents (GitHub Copilot, Codex, other automated systems) should support the following tasks:

### Module Development

* **NOW (Ingest):** Design ingestion pipelines capable of handling text files initially, with iterative expansion into audio, video, and sensor data.
* **EXPRESS (Semantic Encoding):** Implement semantic vectorization methods using sentence-transformers, NLP preprocessing pipelines, and standardized schema outputs.
* **INTERPRET (Semantic Pruning & Refinement):** Develop NLP methods for pruning irrelevant content and refining semantic accuracy.
* **REFLECT (Truth Anchoring):** Create systems to validate semantic vectors against established truth criteria or benchmarks.
* **VISUALIZE (Insight Generation):** Build visualization components capable of translating semantic vectors into insightful visual formats (charts, graphs, cognitive maps).
* **EMBED (Semantic Memory Storage):** Integrate with Qdrant for semantic memory embedding and PostgreSQL for structured metadata storage.

### Operational Guidelines

* **Pull Requests (PRs):** Clearly label PRs with module and functionality, e.g., `[EXPRESS] - Semantic Vectorization`.
* **Testing Requirements:** All PRs must include unit tests validating critical functionality.
* **Documentation:** Comprehensive comments, docstrings, and structured API documentation are mandatory for all contributions.
* **Formatting and Style:** Adhere to Python PEP8, Black formatting standards, and strict type hints. JavaScript/TypeScript should follow industry-standard practices.

### Constraints and Guardrails

* Do **NOT** modify the database schema without explicit confirmation.
* Avoid committing binary files or large datasets directly; utilize Git LFS or external storage.
* Clearly document termination conditions for recursive or looping processes to prevent unintended infinite loops.
* Avoid using insecure libraries or frameworks without explicit approval.

### Preferred Tools and Conventions

* **Languages and Frameworks:**

  * Python (FastAPI, PyTorch, sentence-transformers)
  * JavaScript/TypeScript (React)
* **Databases and Storage:**

  * Semantic Memory: Qdrant
  * Structured Metadata: PostgreSQL
* **Containerization and Infrastructure:**

  * Docker Compose
  * Kubernetes (future phase)
* **Logging and Monitoring:**

  * Structured logging (JSON format)
  * Prometheus/Grafana stack (future integration)

## Next Steps

* Regularly review and update this document as project requirements evolve.
* Validate agent behavior periodically to ensure adherence to these guidelines.

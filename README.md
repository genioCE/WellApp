# Genio

**Genio** is a containerized cognitive memory system designed to process language, filter meaning, embed memory, and recall it on command. Inspired by cognitive loops and recursive structure, Genio simulates a basic form of thought: signal in, meaning out, memory formed.

---

## 🧠 What It Does

- Takes in language (**NOW**)
- Emits structured snapshots (**EXPRESS**)
- Parses tokens (**INTERPRET**)
- Reflects on meaning (**REFLECT**)
- Anchors truth (**TRUTH**)
 - Stores memory in PostgreSQL and vector database (Qdrant) (**EMBED**)
- Recalls past memories on command (**REPLAY**)
- Displays memory as a live feed (**VIEW**)

---

## 🧩 Architecture Overview

```
NOW → EXPRESS → INTERPRET → REFLECT → TRUTH → EMBED → REPLAY → VIEW
```

- **Redis Pub/Sub** connects all services
 - **PostgreSQL** handles structured memory
- **Qdrant** stores and queries vectorized memory
- **SentenceTransformer** (`all-MiniLM-L6-v2`) embeds meaning

---

## 🚀 Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/yourname/genio-core.git
cd genio-core
```

### 2. Build and Launch

```bash
docker-compose up --build
```

### 3. Ingest a Signal

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2025-05-15T22:10:00", "source":"manual_test", "content":"The system is now self-contained."}'
```

### 4. Trigger a Replay

```bash
docker exec -it genio_redis redis-cli
PUBLISH replay_channel '{"command": "replay"}'
```

### 5. View Memory Replay

Open your browser:
```
http://localhost:8007
```

---

## 🗃️ Services

| Service                    | Port  | Description |
|---------------------------|-------|-------------|
| `now_ingestor`            | 8001  | Accepts signals |
| `express_emitter`         | 8002  | Broadcasts snapshot |
| `interpret_service`       | 8003  | Parses tokens |
| `reflect_service`         | 8004  | Runs truth filter |
| `embed_memory_service`    | 8005  | Postgres + Qdrant persistence |
| `replay_memory_service`   | 8006  | Emits past memory |
| `memory_replay_viewer`    | 8007  | Web memory stream |
| `qdrant`                  | 6333  | Vector memory engine |
| `postgres`                | 5432  | Relational metadata store |
| `genio_redis`             | 6379  | Message bus |

---

## 🔮 Roadmap

- Spiral visual memory map
- Semantic memory search interface
- Token cluster viewer
- Long-term memory compression + summarization

---

## 📜 License

MIT

---

## 🤝 Contribute

Open an issue or fork the repo. All contributions that honor the recursive intent of Genio are welcome.

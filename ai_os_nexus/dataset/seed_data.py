"""
Seed Data — populates the knowledge base on first startup.
~50+ entries covering general knowledge, programming, science,
irrigation best practices, medical vital ranges, industrial safety.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SEED_ENTRIES = [
    # ── General Knowledge ──────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "The speed of light in a vacuum is approximately 299,792,458 metres per second (c). It is a fundamental physical constant and the maximum speed at which information or matter can travel.",
        "source": "physics_constants",
        "metadata": {"topic": "physics", "subtopic": "constants"},
    },
    {
        "category": "knowledge",
        "content": "Water (H₂O) boils at 100°C (212°F) at standard atmospheric pressure (1 atm = 101.325 kPa). The boiling point decreases at higher altitudes due to lower atmospheric pressure.",
        "source": "chemistry_basics",
        "metadata": {"topic": "chemistry", "subtopic": "phase_transitions"},
    },
    {
        "category": "knowledge",
        "content": "The human brain contains approximately 86 billion neurons. Each neuron can form up to 10,000 synaptic connections with other neurons, giving the brain an estimated 100 trillion synapses.",
        "source": "neuroscience",
        "metadata": {"topic": "biology", "subtopic": "neuroscience"},
    },
    {
        "category": "knowledge",
        "content": "Newton's three laws of motion: (1) An object at rest stays at rest unless acted upon by a force. (2) F = ma (force equals mass times acceleration). (3) For every action there is an equal and opposite reaction.",
        "source": "physics_basics",
        "metadata": {"topic": "physics", "subtopic": "mechanics"},
    },
    {
        "category": "knowledge",
        "content": "The Earth is approximately 4.54 billion years old. It is the third planet from the Sun and the only known celestial body to harbour life. Its atmosphere is 78% nitrogen, 21% oxygen, and 1% other gases.",
        "source": "earth_science",
        "metadata": {"topic": "science", "subtopic": "earth_science"},
    },
    {
        "category": "knowledge",
        "content": "DNA (deoxyribonucleic acid) is the hereditary material in humans and almost all other organisms. It is a double helix composed of four nucleotide bases: adenine (A), thymine (T), guanine (G), and cytosine (C).",
        "source": "molecular_biology",
        "metadata": {"topic": "biology", "subtopic": "genetics"},
    },
    {
        "category": "knowledge",
        "content": "Photosynthesis is the process by which plants, algae, and some bacteria convert light energy into chemical energy. The overall equation is: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂.",
        "source": "biology_basics",
        "metadata": {"topic": "biology", "subtopic": "biochemistry"},
    },
    {
        "category": "knowledge",
        "content": "The periodic table organises all known chemical elements by atomic number. It has 118 confirmed elements arranged in 18 groups (columns) and 7 periods (rows). Elements in the same group share similar chemical properties.",
        "source": "chemistry_basics",
        "metadata": {"topic": "chemistry", "subtopic": "periodic_table"},
    },
    {
        "category": "knowledge",
        "content": "Climate change refers to long-term shifts in global temperatures and weather patterns. Human activities since the mid-20th century have been the primary driver, mainly through burning fossil fuels which increases atmospheric CO₂.",
        "source": "environmental_science",
        "metadata": {"topic": "science", "subtopic": "climate"},
    },
    {
        "category": "knowledge",
        "content": "Artificial intelligence (AI) refers to systems or machines that simulate human intelligence to perform tasks and improve themselves based on the information they collect. Key subfields include machine learning, deep learning, and natural language processing.",
        "source": "cs_fundamentals",
        "metadata": {"topic": "technology", "subtopic": "ai"},
    },

    # ── Programming ────────────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "Python is an interpreted, high-level, general-purpose programming language emphasising code readability. It uses indentation for block structure. Key features: dynamic typing, garbage collection, extensive standard library.",
        "source": "programming_python",
        "metadata": {"topic": "programming", "language": "python"},
    },
    {
        "category": "knowledge",
        "content": "REST (Representational State Transfer) is an architectural style for distributed hypermedia systems. Key constraints: stateless, client-server, cacheable, uniform interface. HTTP methods: GET (read), POST (create), PUT (update), DELETE (remove).",
        "source": "web_development",
        "metadata": {"topic": "programming", "subtopic": "web_apis"},
    },
    {
        "category": "knowledge",
        "content": "Big O notation describes the worst-case time complexity of algorithms. Common complexities: O(1) constant, O(log n) logarithmic, O(n) linear, O(n log n) linearithmic, O(n²) quadratic, O(2ⁿ) exponential.",
        "source": "cs_algorithms",
        "metadata": {"topic": "programming", "subtopic": "algorithms"},
    },
    {
        "category": "knowledge",
        "content": "SQL (Structured Query Language) is the standard language for relational databases. Key commands: SELECT (query), INSERT (add), UPDATE (modify), DELETE (remove). Joins combine rows from multiple tables: INNER, LEFT, RIGHT, FULL OUTER.",
        "source": "databases",
        "metadata": {"topic": "programming", "subtopic": "databases"},
    },
    {
        "category": "knowledge",
        "content": "Git is a distributed version control system. Key commands: git init (initialise), git add (stage), git commit (save), git push (upload), git pull (download), git branch (manage branches), git merge (combine branches).",
        "source": "devops",
        "metadata": {"topic": "programming", "subtopic": "version_control"},
    },
    {
        "category": "knowledge",
        "content": "Docker is a containerisation platform. Containers package application code with dependencies for consistent deployment. Key concepts: images (templates), containers (running instances), Dockerfile (build instructions), docker-compose (multi-container apps).",
        "source": "devops",
        "metadata": {"topic": "programming", "subtopic": "devops"},
    },
    {
        "category": "knowledge",
        "content": "FastAPI is a modern, high-performance Python web framework for building APIs. It uses Python type hints for automatic OpenAPI documentation. Supports async/await natively. Built on Starlette and Pydantic.",
        "source": "programming_python",
        "metadata": {"topic": "programming", "subtopic": "web_frameworks", "language": "python"},
    },
    {
        "category": "knowledge",
        "content": "Async programming allows programs to perform multiple operations concurrently without creating threads. In Python, async/await syntax with asyncio enables writing coroutines. Particularly useful for I/O-bound tasks like network requests and file operations.",
        "source": "programming_python",
        "metadata": {"topic": "programming", "subtopic": "concurrency"},
    },

    # ── Irrigation Best Practices ──────────────────────────────────────
    {
        "category": "knowledge",
        "content": "Optimal soil moisture for most crops is between 40–60%. Below 35% triggers water stress and reduced yields. Above 80% causes waterlogging, root rot, and oxygen deprivation. Monitor using capacitance probes or tensiometers.",
        "source": "irrigation_agronomy",
        "metadata": {"topic": "irrigation", "subtopic": "soil_moisture"},
    },
    {
        "category": "knowledge",
        "content": "Drip irrigation (micro-irrigation) delivers water directly to the root zone at low flow rates. It reduces evaporation losses by 40–60% compared to flood irrigation and minimises weed growth between rows. Best for row crops, orchards, and vineyards.",
        "source": "irrigation_systems",
        "metadata": {"topic": "irrigation", "subtopic": "drip_systems"},
    },
    {
        "category": "knowledge",
        "content": "Evapotranspiration (ET) is the combined water loss from soil evaporation and plant transpiration. ET increases with temperature, wind speed, solar radiation, and low humidity. Reference ET (ET₀) is the standard used to calculate crop water requirements.",
        "source": "irrigation_agronomy",
        "metadata": {"topic": "irrigation", "subtopic": "evapotranspiration"},
    },
    {
        "category": "knowledge",
        "content": "Irrigation scheduling: irrigate when soil moisture drops to 50% of plant-available water (PAW) for most field crops. For fruits and vegetables, maintain 60–70% PAW. Avoid irrigation when rain probability exceeds 60% in the next 24 hours.",
        "source": "irrigation_scheduling",
        "metadata": {"topic": "irrigation", "subtopic": "scheduling"},
    },
    {
        "category": "knowledge",
        "content": "Water pressure in irrigation systems should be maintained at 1.5–4 bar for drip systems and 2–4 bar for sprinkler systems. Over-pressure (>8 bar) risks pipe bursts and requires emergency shutoff. Under-pressure (<0.5 bar) results in inadequate coverage.",
        "source": "irrigation_systems",
        "metadata": {"topic": "irrigation", "subtopic": "pressure_management"},
    },
    {
        "category": "knowledge",
        "content": "Cover crops (e.g., clover, rye) improve soil water retention by 15–25% and reduce erosion. Mulching with organic material reduces soil surface evaporation by up to 70% and maintains more uniform soil moisture levels.",
        "source": "soil_management",
        "metadata": {"topic": "irrigation", "subtopic": "soil_management"},
    },

    # ── Medical Vital Ranges ───────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "Normal adult heart rate (pulse): 60–100 beats per minute (bpm). Bradycardia: <60 bpm. Tachycardia: >100 bpm. Critical alert thresholds: <40 bpm or >150 bpm require immediate clinical evaluation.",
        "source": "medical_vitals",
        "metadata": {"topic": "medical", "subtopic": "heart_rate"},
    },
    {
        "category": "knowledge",
        "content": "Normal adult blood pressure: systolic 90–120 mmHg, diastolic 60–80 mmHg. Stage 1 hypertension: 130–139/80–89. Stage 2: ≥140/90. Hypertensive crisis: ≥180/120 (requires emergency care). Hypotension: <90/60.",
        "source": "medical_vitals",
        "metadata": {"topic": "medical", "subtopic": "blood_pressure"},
    },
    {
        "category": "knowledge",
        "content": "Normal blood oxygen saturation (SpO₂): 95–100%. Mild hypoxemia: 91–94% (supplemental O₂ recommended). Moderate: 86–90% (urgent medical evaluation). Severe/critical: <85% (immediate intervention required).",
        "source": "medical_vitals",
        "metadata": {"topic": "medical", "subtopic": "oxygen_saturation"},
    },
    {
        "category": "knowledge",
        "content": "Normal body temperature: 36.1–37.2°C (97–99°F). Low-grade fever: 37.3–38.0°C. Fever: 38.1–39.0°C. High fever: >39.1°C. Hyperpyrexia: >40°C (medical emergency). Hypothermia: <35°C (medical emergency).",
        "source": "medical_vitals",
        "metadata": {"topic": "medical", "subtopic": "temperature"},
    },
    {
        "category": "knowledge",
        "content": "Normal adult respiratory rate: 12–20 breaths per minute. Tachypnea (fast breathing): >20/min. Bradypnea (slow breathing): <12/min. Critical: <8 or >30 breaths per minute indicates respiratory failure risk.",
        "source": "medical_vitals",
        "metadata": {"topic": "medical", "subtopic": "respiratory_rate"},
    },
    {
        "category": "knowledge",
        "content": "Glasgow Coma Scale (GCS) measures consciousness: Eye opening (1–4), Verbal response (1–5), Motor response (1–6). Total 13–15: mild injury/normal. 9–12: moderate. 3–8: severe (intubation typically required). Score of 3 = deep unconsciousness.",
        "source": "medical_assessment",
        "metadata": {"topic": "medical", "subtopic": "neurological"},
    },
    {
        "category": "knowledge",
        "content": "Early Warning Score (EWS) tracks deterioration using 6 parameters: respiratory rate, SpO₂, blood pressure, heart rate, temperature, consciousness. Score 0–4: low risk. 5–6: medium (urgent review). ≥7: high risk (emergency response).",
        "source": "medical_monitoring",
        "metadata": {"topic": "medical", "subtopic": "early_warning"},
    },

    # ── Industrial Safety ──────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "Industrial pressure vessel safety: ASME codes specify maximum allowable working pressure (MAWP). Pressure relief valves must be set to ≤1.1 × MAWP. Safety inspections every 1–2 years. Operating above MAWP is prohibited and constitutes an emergency.",
        "source": "industrial_safety",
        "metadata": {"topic": "industrial", "subtopic": "pressure_safety"},
    },
    {
        "category": "knowledge",
        "content": "Machine vibration monitoring: ISO 10816 standards define acceptable vibration levels. RMS velocity >4.5 mm/s (Class I) signals unsatisfactory condition. >7.1 mm/s = danger zone requiring immediate shutdown. Common causes: imbalance, misalignment, bearing wear.",
        "source": "industrial_maintenance",
        "metadata": {"topic": "industrial", "subtopic": "vibration"},
    },
    {
        "category": "knowledge",
        "content": "Industrial temperature monitoring: Class H insulation in motors rated for 180°C. Bearing overtemperature (>90°C) indicates insufficient lubrication or overloading. Transformer windings above rated temperature reduce insulation life by 50% for every 10°C increase (Arrhenius rule).",
        "source": "industrial_safety",
        "metadata": {"topic": "industrial", "subtopic": "temperature"},
    },
    {
        "category": "knowledge",
        "content": "Lock-out/Tag-out (LOTO) procedure prevents accidental energisation during maintenance. Steps: (1) Notify affected workers. (2) Identify all energy sources. (3) Isolate energy. (4) Apply locks and tags. (5) Release stored energy. (6) Verify isolation before work begins.",
        "source": "industrial_safety",
        "metadata": {"topic": "industrial", "subtopic": "loto"},
    },
    {
        "category": "knowledge",
        "content": "Programmable Logic Controllers (PLCs) are ruggedised computers used for industrial automation. They execute ladder logic or structured text programs in real-time scan cycles (typically 1–100 ms). Watchdog timers restart the PLC if the scan cycle exceeds its limit.",
        "source": "industrial_automation",
        "metadata": {"topic": "industrial", "subtopic": "plc"},
    },
    {
        "category": "knowledge",
        "content": "SCADA (Supervisory Control and Data Acquisition) systems monitor and control industrial processes remotely. Components: field devices (sensors/actuators), RTUs/PLCs (local control), communications network, SCADA server, HMI (human-machine interface).",
        "source": "industrial_automation",
        "metadata": {"topic": "industrial", "subtopic": "scada"},
    },

    # ── AI/ML Knowledge ────────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "Large Language Models (LLMs) are neural networks trained on massive text corpora to understand and generate human language. They use transformer architecture with self-attention mechanisms. Examples: GPT-4, Llama, Mistral, Claude.",
        "source": "ai_fundamentals",
        "metadata": {"topic": "ai", "subtopic": "llm"},
    },
    {
        "category": "knowledge",
        "content": "Vector embeddings represent text, images, or other data as dense numerical vectors in a high-dimensional space. Semantically similar items have vectors with high cosine similarity. Used for semantic search, recommendation systems, and RAG (Retrieval-Augmented Generation).",
        "source": "ai_fundamentals",
        "metadata": {"topic": "ai", "subtopic": "embeddings"},
    },
    {
        "category": "knowledge",
        "content": "Retrieval-Augmented Generation (RAG) combines a retrieval system with a generative LLM. The retrieval system finds relevant documents from a knowledge base; the LLM uses these as context to generate accurate, grounded responses. Reduces hallucinations significantly.",
        "source": "ai_fundamentals",
        "metadata": {"topic": "ai", "subtopic": "rag"},
    },
    {
        "category": "knowledge",
        "content": "TF-IDF (Term Frequency–Inverse Document Frequency) measures word importance in a document relative to a corpus. TF = frequency of term in document. IDF = log(N/df) where N = total documents and df = documents containing the term. High TF-IDF = distinctive term.",
        "source": "ai_nlp",
        "metadata": {"topic": "ai", "subtopic": "nlp"},
    },
    {
        "category": "knowledge",
        "content": "Cosine similarity measures the angle between two vectors. Formula: cos(θ) = (A·B) / (||A|| × ||B||). Range: -1 (opposite) to 1 (identical). Used in NLP for document similarity, clustering, and semantic search. Value >0.8 typically indicates high similarity.",
        "source": "ai_math",
        "metadata": {"topic": "ai", "subtopic": "similarity_metrics"},
    },

    # ── Privacy & Security ─────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "GDPR (General Data Protection Regulation) gives EU citizens rights over their personal data: right of access, rectification, erasure (right to be forgotten), portability, and objection. Controllers must have lawful basis for processing and notify breaches within 72 hours.",
        "source": "data_privacy",
        "metadata": {"topic": "security", "subtopic": "gdpr"},
    },
    {
        "category": "knowledge",
        "content": "AES-256 (Advanced Encryption Standard) is a symmetric block cipher using 256-bit keys. It is considered unbreakable with current computing power. Fernet (used in Python cryptography library) implements AES-128-CBC with HMAC-SHA256 authentication.",
        "source": "cybersecurity",
        "metadata": {"topic": "security", "subtopic": "encryption"},
    },
    {
        "category": "knowledge",
        "content": "PBKDF2 (Password-Based Key Derivation Function 2) derives a cryptographic key from a password using a salt and many iterations (e.g., 100,000). The iterations make brute-force attacks computationally expensive. Used in password hashing and key derivation.",
        "source": "cybersecurity",
        "metadata": {"topic": "security", "subtopic": "key_derivation"},
    },

    # ── IoT/Sensors ────────────────────────────────────────────────────
    {
        "category": "knowledge",
        "content": "MQTT (Message Queuing Telemetry Transport) is a lightweight publish-subscribe protocol for IoT. Broker mediates between publishers and subscribers. QoS levels: 0 (at most once), 1 (at least once), 2 (exactly once). Port 1883 (plain), 8883 (TLS).",
        "source": "iot_protocols",
        "metadata": {"topic": "iot", "subtopic": "protocols"},
    },
    {
        "category": "knowledge",
        "content": "Capacitive soil moisture sensors measure the dielectric permittivity of soil, which changes with water content. They are more accurate and durable than resistive sensors. Output: 0–3V (dry to wet) or 0–100% relative soil moisture percentage.",
        "source": "iot_sensors",
        "metadata": {"topic": "iot", "subtopic": "soil_sensors"},
    },
    {
        "category": "knowledge",
        "content": "Edge computing processes data near the source (IoT device) rather than sending all data to a cloud server. Benefits: reduced latency (sub-millisecond decisions), lower bandwidth costs, privacy (data stays local), resilience to connectivity loss.",
        "source": "iot_architecture",
        "metadata": {"topic": "iot", "subtopic": "edge_computing"},
    },
]


def seed_dataset(dataset_manager, force: bool = False) -> int:
    """
    Seed the dataset with initial knowledge entries.
    
    Args:
        dataset_manager: DatasetManager instance
        force: If True, re-seed even if data already exists
    
    Returns:
        Number of entries added
    """
    if not force and dataset_manager.count() >= 20:
        logger.info("Dataset already has %d entries — skipping seed", dataset_manager.count())
        return 0

    logger.info("Seeding dataset with %d entries...", len(SEED_ENTRIES))
    count = 0
    for entry in SEED_ENTRIES:
        try:
            dataset_manager.add_entry(
                category=entry["category"],
                content=entry["content"],
                source=entry.get("source", "seed"),
                metadata=entry.get("metadata", {}),
            )
            count += 1
        except Exception as exc:
            logger.error("Failed to seed entry: %s", exc)

    logger.info("Seeded %d entries into dataset", count)
    return count

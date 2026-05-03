# Magicpin Vera AI Challenge Solution

This repository contains a production-ready FastAPI service for the Magicpin Vera AI Challenge.

## App structure

- `app/main.py` — FastAPI application entrypoint.
- `app/routes/` — HTTP endpoints for health, metadata, context ingestion, tick processing, and reply handling.
- `app/services/` — scoring, decision engine, message generation, and in-memory context storage.
- `app/models/` — Pydantic schema examples for merchant, customer, and trigger payloads.
- `app/utils/logger.py` — simple logging configuration.

## Installation

```bash
cd "c:\Users\kowsh\Desktop\Magic Pin"
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API endpoints

### GET /v1/healthz

```json
{ "status": "ok" }
```

### GET /v1/metadata

```json
{
  "name": "Vera AI Bot",
  "version": "1.0",
  "description": "AI engagement assistant for merchants"
}
```

### POST /v1/context

Ingest merchant, customer, and trigger context.

Example request:

```json
{
  "merchant": { "merchant_id": "m_001_drmeera_dentist_delhi", "category_slug": "dentists", "identity": { "name": "Dr. Meera's Dental Clinic" } },
  "customer": { "customer_id": "c_001_priya_for_m001", "merchant_id": "m_001_drmeera_dentist_delhi", "identity": { "name": "Priya" }, "relationship": { "last_visit": "2026-05-12", "visits_total": 4 }, "state": "lapsed_soft" },
  "trigger": { "id": "trg_003_recall_due_priya", "scope": "customer", "kind": "recall_due", "merchant_id": "m_001_drmeera_dentist_delhi", "customer_id": "c_001_priya_for_m001", "payload": { "service_due": "6_month_cleaning" }, "urgency": 3 }
}
```

### POST /v1/tick

Process an event and decide target customers.

Example response:

```json
{
  "status": "ok",
  "tick_id": "tick-001",
  "merchant_id": "m_001_drmeera_dentist_delhi",
  "trigger_id": "trg_003_recall_due_priya",
  "decisions": [
    {
      "customer_id": "c_001_priya_for_m001",
      "merchant_id": "m_001_drmeera_dentist_delhi",
      "decision": "send",
      "score": 0.82,
      "explain": "category_match=1.00, recency=0.85, frequency=0.65",
      "message": "Hey Priya, your 6 month cleaning is due at Dr. Meera's Dental Clinic. We can book it tomorrow evening. Reply YES to confirm.",
      "cta": "YES",
      "best_time": "weekday evening",
      "why": "Recall reminder focused on specific service and booking urgency."
    }
  ],
  "summary": { "count": 1, "average_score": 0.82 }
}
```

### POST /v1/reply

Generate a follow-up response to user replies.

Example request:

```json
{
  "merchant_id": "m_001_drmeera_dentist_delhi",
  "customer_id": "c_001_priya_for_m001",
  "message": "Yes please book it",
  "reply_type": "customer"
}
```

Example response:

```json
{
  "status": "ok",
  "merchant_id": "m_001_drmeera_dentist_delhi",
  "customer_id": "c_001_priya_for_m001",
  "reply": "Great Priya! I will confirm the booking with Dr. Meera's Dental Clinic and send you details shortly.",
  "next_action": "confirm_booking",
  "explain": "The reply indicates customer intent, so we confirm and move to booking."
}
```

## Deployment

### Render

1. Create a new Python web service in Render.
2. Connect the repository.
3. Set the start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Ensure `requirements.txt` is present.

Render will automatically install dependencies and start the app.

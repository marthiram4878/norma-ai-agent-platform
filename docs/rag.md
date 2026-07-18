# RAG / Knowledge Engine

Norma indexes uploaded documents into PostgreSQL + Qdrant and retrieves them
with dense embeddings (BGE-M3) for grounded answers.

## Supported uploads

- PDF
- DOCX
- Markdown
- TXT

Bounded by `MAX_UPLOAD_SIZE_BYTES`, chunk size, and overlap from settings.

## Ingest path (async)

```text
POST /api/v1/knowledge/documents  → 202
  → Document(status=pending) + document_uploads blob
  → Redis job (knowledge_ingest)
  → worker: parse → chunk → embed → Qdrant → completed|failed
```

Poll status via `GET /api/v1/knowledge/documents/{id}` or list documents.
Failed runs store a short `error` on the document row.

Launch Strategy packs call `KnowledgeService.ingest` synchronously **inside**
the worker (not over HTTP).

## Tenancy filters

Every chunk payload includes:

- `workspace_id`
- `space_id`
- `document_id`
- `source_type=document` (new writes)

Retrieval always filters by workspace (and space when provided). Document
search excludes `source_type=memory` so memory notes do not appear as citations.
Legacy points without `source_type` remain searchable as documents.

## Retrieve → generate

The RAG Assistant workflow:

1. Embed the question  
2. Query Qdrant with tenant filters  
3. If no hits → refuse to invent from empty context  
4. Else → OpenRouter completion with citation instructions  

Embeddings run in a separate Compose service (`embedding_service`) so API and
GPU/CPU embedding capacity scale independently.

## Related code

- `backend/app/rag/` — parse, chunk, embeddings, vector store, retriever  
- `backend/app/services/knowledge.py` — enqueue / execute ingest  
- `backend/app/workflows/rag_assistant.py` — LangGraph assistant  

See also: [architecture.md](architecture.md), [api.md](api.md).

# Memory

Norma keeps two complementary memory layers: conversational history and
workspace notes. Both are scoped by workspace, knowledge space, and user where
applicable.

## Conversation memory

Tables: `conversations`, `conversation_messages`.

- Created/continued via `conversation_id` on `POST /assistant/query`
- Listed with `GET /assistant/conversations`
- Messages via `GET /assistant/conversations/{id}/messages`
- Recent turns are injected into the RAG Assistant prompt as chat context

## Workspace memory notes

Table: `workspace_memories`.

Today the primary writer is Launch Strategy completion:

- kind: `workflow_summary`
- content: short markdown summary of the run
- linked `source_run_id`

On write, Norma also embeds the note into Qdrant:

```text
source_type=memory
workspace_id, space_id, memory_id, kind, content
```

## Loading notes for the assistant

`MemoryService.load_workspace_notes`:

1. Semantic retrieve (`source_type=memory`, top-k) for the current question  
2. If empty / failed → SQL `ORDER BY created_at DESC LIMIT N`

Notes are supporting context only — not citation-grade knowledge documents.

## What memory is not (yet)

- User preference profiles as first-class entities  
- Cross-space memory sharing  
- Automatic note extraction from every chat turn  
- Dedicated reranking over memory hits  

See also: [agents.md](agents.md), [rag.md](rag.md).

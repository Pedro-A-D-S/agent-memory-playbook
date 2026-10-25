# The 5-Layer Agent Memory Architecture

> Independent compilation based on CoALA, Mem0, Anthropic memory systems,
> Snowflake ontology research, and LangChain production materials. It is
> **not affiliated with, or endorsed by, Anthropic, Mem0, Snowflake, or any other
> organisation.**

## The problem

Every model call starts with an empty context window. Sessions end; discoveries,
decisions, corrections and preferences do not survive. Re-briefing the agent every
morning costs the same tokens as the first day, every day.

## The five layers

| Layer | Stores | Retrieval | Expiration |
| --- | --- | --- | --- |
| 1. Working | Current context window | Always loaded | End of call |
| 2. Episodic | What happened (task, approach, outcome, errors) | By similarity | 30–90 days |
| 3. Semantic | What is true (facts, entities, relations) | By entity / query | On supersession |
| 4. Procedural | How to do things (reusable skills) | By trigger match | On version update |
| 5. Forgetting | What to delete | Scheduled | Continuous |

## Data flow

Working memory overflows → episodic memory. Repeated episodic patterns distil into
semantic facts. Reliable semantic methods are promoted to procedural skills. The
forgetting engine expires, supersedes and flags contradictions.

## Evidence cited by the architecture

| Metric | Without memory | With memory | Source |
| --- | --- | --- | --- |
| Tokens per query | 26,000 | 1,800 | Mem0 |
| Latency | baseline | −91% | Mem0 |
| Accuracy | baseline | +20% | Snowflake |
| Tool calls | baseline | −39% | Snowflake |

## Anti-patterns

Store everything · never expire · no schema · no retrieval · one big store ·
no versioning · storing raw context.

## Production checklist

1. Episodic log saves task outcomes
2. Episodic retrieval before new tasks
3. Semantic store for durable facts
4. Ontology schema validates entries
5. Conflict resolution for semantic facts
6. Procedural skills from repeated success
7. Skill versioning with rollback
8. Expiration policy for episodes
9. Context overflow handler
10. Forgetting engine runs on schedule

## Seven-day build path

| Day | Build | Exit test |
| --- | --- | --- |
| 1 | Episodic log (JSON) | Agent recalls yesterday's failure |
| 2 | Retrieval before starting | Agent skips known dead ends |
| 3 | Semantic store | Agent knows user preferences |
| 4 | Ontology schema | Store validates against schema |
| 5 | Procedural skills | Agent uses the saved method |
| 6 | Forgetting | No contradictions in store |
| 7 | Wire the full pipeline | Multi-session task runs end-to-end |

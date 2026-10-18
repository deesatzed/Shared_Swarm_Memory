# Aether model configuration

The user-selected order, refreshed 2026-10-18, is defined in `model_config.py`.

| Purpose | Default | Alternatives | OpenRouter endpoint |
| --- | --- | --- | --- |
| Text | `deepseek/deepseek-v4.1-flash-1017` | `nvidia/nemotron-3.5-super-vl`, `google/gemini-4-argon` | `/api/v1/chat/completions` |
| Decisions | `liquid/d1-ultra` | `typesafe/jev-1.14` | `/api/v1/systemone` |
| Embeddings | `google/gemini-embedding-2` | `liquid/lfm-2.5-embedding-350m:free` | `/api/v1/embeddings` |

Decision models return typed answers and probabilities. They cannot replace a
text model in the chat client. `OpenRouterFrozenLLM.decide(state, questions)`
uses this contract; `generate(system_prompt, user_prompt)` remains text-only.

Embeddings use the requested model without automatic fallback. Each embedding
model needs its own index or a full re-embedding migration; equal dimensions do
not make embedding spaces interchangeable. `embed(inputs, model=...)` selects
an alternative explicitly. The main repo's Hy-Memory index is still unfinished.

Credentials can come from `OPENROUTER_API_KEY`, an explicit `credentials_file`
argument, or `AETHER_CREDENTIALS_FILE`. Only the selected key is read from a file.
Other settings and secrets in that file are not imported, and shell commands are
never executed. Explicit credential files take precedence over the environment.

```sh
export AETHER_CREDENTIALS_FILE=/Volumes/WS4TB/merged.env
# Optional text override; the approved default is DeepSeek.
export MODEL1=google/gemini-4-argon
python aether_cli2.py --help
```

`DECISION_MODEL` and `EMBED_MODEL` similarly select the first model within their
approved group. A credential file supplies only the key; it cannot override these
model choices. `.env.example` lists settings but is not automatically loaded.

Explicit live checks send only short generic connection inputs, one request per
model, with fallback disabled so each result belongs to the requested model:

```sh
python scripts/check_models.py --credentials-file /Volumes/WS4TB/merged.env --output receipts/model-check.json
python -m unittest discover -s tests -v
```

These checks validate access and response shape, not decision accuracy or swarm
quality. The runtime still uses its existing rule router; the model refresh does
not implement recursive improvement or connect the main memory decision service.

Sources: [System One API](https://openrouter.ai/docs/guides/community/typesafe-sdk),
[embedding API](https://openrouter.ai/docs/api_reference/embeddings).

# Compresr Guardrail — query-aware, recoverable context compression

[Compresr](https://compresr.ai) compresses bulky message content (tool outputs,
RAG chunks, search results) before the request reaches the LLM, cutting prompt
tokens without losing the information the model actually needs for the current
question.

Two things set it apart from whole-conversation compressors:

- **Query-aware:** each message is compressed against the *intent* that
  produced it — for a tool output, the originating tool call's
  `name + arguments` (resolved via `tool_call_id`); otherwise the last user
  message. Content relevant to the question survives; noise goes.
- **Recoverable, not lossy:** every compressed message carries a
  `compresr hash=<...>` marker and the request gains a `compresr_retrieve`
  tool. If the model finds the compressed version insufficient, it calls the
  tool and LiteLLM's agentic loop transparently feeds the original content
  back — no application changes.

## Quickstart

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o

guardrails:
  - guardrail_name: compresr
    litellm_params:
      guardrail: compresr
      mode: pre_call
      default_on: true
      api_key: os.environ/COMPRESR_API_KEY
```

That's it. Tool/function outputs longer than 500 characters are now compressed
~2x, query-aware, on `/chat/completions`, `/v1/messages`, and `/v1/responses`.

## Configuration

| Key | Default | Meaning |
| --- | --- | --- |
| `api_key` | `COMPRESR_API_KEY` env | Compresr API key (`cmp_...`) |
| `api_base` | `https://api.compresr.ai` | Point at your on-prem Compresr deployment |
| `model` | `latte_v2` | Compresr compression model (not the LLM) |
| `unreachable_fallback` | `fail_closed` | `fail_open` forwards uncompressed when Compresr is down |

Optional tuning, under `optional_params`:

| Key | Default | Meaning |
| --- | --- | --- |
| `target_compression_ratio` | `0.5` | 0–1 = fraction of tokens to remove; >1 = Nx reduction factor |
| `coarse` | `true` | Paragraph-level (faster) vs token-level compression |
| `min_chars_to_compress` | `500` | Skip messages shorter than this |
| `compress_tool_outputs` | `true` | Compress tool/function results |
| `compress_system` | `false` | Also compress system messages |
| `compress_history` | `false` | Also compress prior user messages |
| `compress_last_user` | `false` | Also compress the last user message |
| `enable_retrieval` | `true` | Inject the `compresr_retrieve` recovery tool |
| `dynamic` | `false` | latte_v2 only: let the server pick the ratio per input instead of `target_compression_ratio` |
| `dynamic_min_ratio` | server default | Floor on the adaptive ratio when `dynamic` is on |
| `dynamic_max_ratio` | server default | Ceiling on the adaptive ratio when `dynamic` is on |
| `max_bytes_per_call` | `10 MiB` | Cap on aggregate bytes of stored originals per `litellm_call_id` |
| `allow_bypass_header` | `false` | Honor the `x-compresr-bypass` request header (see below) |
| `compression_params` | none | Extra Compresr params forwarded verbatim in the compress payload |

## Per-request bypass

Set `allow_bypass_header: true` under `optional_params` (off by default,
because the header is caller-settable), then send `x-compresr-bypass: true`
as a request header to skip compression for a single call. With
`allow_bypass_header` unset, the header is ignored.

## How recovery works

1. `apply_guardrail` compresses eligible messages and appends a marker:
   `[compresr hash=abc...: parts of this content were compressed away ...]`.
   The original text is kept in-process, scoped to this request's
   `litellm_call_id` (15-minute TTL).
2. A `compresr_retrieve` tool is merged into the request's tools.
3. If the model calls it, `async_build_agentic_loop_plan` answers the tool
   call with the stored original and re-runs the request — one extra LLM
   round-trip, only when the model asks for it.

Hashes are only honored for the request that issued them; a hash pasted in
from another conversation returns a not-found message instead of content.

## Security & operational notes

- **Recovery store is per-tenant.** Stored originals are keyed by the caller's
  virtual-key hash plus the request's call id, so one caller cannot retrieve
  another's originals even by reusing the (client-settable) `x-litellm-call-id`.
  The store is **in-process**, so for the recovery round-trip to find its
  original the retrieval hop must land on the same worker that stored it; on a
  multi-worker/multi-replica proxy, use sticky routing or accept that a
  cross-worker `compresr_retrieve` returns a not-found marker (the request
  still succeeds, just without the recovered text). The store is also bounded
  by a global entry cap (256) shared across callers, so under heavy multi-tenant
  load a burst from one caller can evict another's still-valid entries early;
  this only degrades the recovery feature (a not-found marker), it never exposes
  one tenant's content to another.
- **`api_base` is trusted operator config.** It is checked against non-http(s)
  schemes and known cloud-metadata addresses (including alternate IP-literal
  encodings) as defense in depth, but this is not a complete SSRF control: the
  shared outbound client follows redirects and re-resolves DNS per request, so
  point `api_base` only at hosts you trust.

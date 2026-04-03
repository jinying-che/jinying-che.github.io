---
title: "Large Language Model Overview"
date: "2026-04-03T23:05:13+0800"
tags: ["large language model", "AI", "transformer"]
description: "A comprehensive overview of Large Language Models — architecture, training, inference, and practical usage"
draft: true
---

# What is LLM?

At its core, LLM is a **next-token predictor**.

Given a sequence of tokens, it predicts the most probable next token. By doing this repeatedly (autoregressive generation), it produces coherent text.

```
Input:  "The cat sat on the"
         ↓ model predicts
Output: "mat"  (probability 0.23)
        "floor" (probability 0.18)
        "roof"  (probability 0.07)
        ...
```

This deceptively simple mechanism — trained on massive text corpora — gives rise to capabilities like translation, code generation, reasoning, and conversation.

## NLP Evolution

| Era | Period | Approach | Example |
|-----|--------|----------|---------|
| Rule-based | 1950s-1980s | Hand-crafted rules, pattern matching | ELIZA (1966) |
| Statistical | 1990s-2000s | N-grams, probabilistic models | IBM Candide MT (1993) |
| Embeddings | 2013-2014 | Dense vector representations | Word2Vec, GloVe |
| Seq2Seq | 2014-2017 | RNN/LSTM with attention | Bahdanau attention (2014) |
| Transformer | 2017 | Self-attention, parallelizable | "Attention Is All You Need" |
| Pre-trained LMs | 2018-2019 | Transfer learning at scale | GPT-1 (117M), BERT (340M) |
| LLM era | 2020+ | Massive scale + alignment | GPT-3 (175B), ChatGPT, GPT-4 |

The key inflection point: the **Transformer** (Vaswani et al., 2017) replaced sequential recurrence with parallelizable self-attention, enabling training on orders-of-magnitude more data.

---

# Transformer Architecture

Nearly all modern LLMs are built on the Transformer. Here's one **Transformer block** (a model stacks N of these, e.g., GPT-3 has 96 layers):

```
              Input Tokens
                   │
                   ▼
        ┌─────────────────────┐
        │  Token Embedding +  │
        │  Positional Encoding│
        └──────────┬──────────┘
                   │
          ┌────────▼────────┐
          │  Multi-Head      │
          │  Self-Attention   │
          └────────┬─────────┘
                   │
          ┌────────▼────────┐
          │  Add & LayerNorm │  ← residual connection
          └────────┬─────────┘
                   │
          ┌────────▼────────┐
          │  Feed-Forward    │
          │  Network (FFN)   │
          └────────┬─────────┘
                   │
          ┌────────▼────────┐
          │  Add & LayerNorm │  ← residual connection
          └────────┬─────────┘
                   │
                   ▼
             × N layers
                   │
                   ▼
        ┌─────────────────────┐
        │  Linear + Softmax   │  → next token probabilities
        └─────────────────────┘
```

## Self-Attention

The core mechanism. Each token computes how much it should "attend to" every other token.

**Step 1**: Project each token into three vectors via learned weight matrices:
- **Q** (Query) — "what am I looking for?"
- **K** (Key) — "what do I contain?"
- **V** (Value) — "what information do I provide?"

**Step 2**: Compute attention scores:
```
Attention(Q, K, V) = softmax(Q·Kᵀ / √d_k) · V
```

The `√d_k` scaling prevents the dot products from growing too large (which would push softmax into regions with tiny gradients).

**Concrete Example** — 3 tokens, d_k = 4:

```
Tokens: ["The", "cat", "sat"]

Q = [[1,0,1,0],   K = [[1,1,0,0],   V = [[0,1,0,1],
     [0,1,0,1],        [0,0,1,1],        [1,0,1,0],
     [1,1,0,0]]        [1,0,1,0]]        [0,0,1,1]]

Step 1: Q·Kᵀ =  [[1, 1, 2],     (raw attention scores)
                  [0, 2, 0],
                  [1, 0, 1]]

Step 2: / √4 =  [[0.5, 0.5, 1.0],
                  [0.0, 1.0, 0.0],
                  [0.5, 0.0, 0.5]]

Step 3: softmax → [[0.26, 0.26, 0.43],   (attention weights, rows sum to 1)
                    [0.21, 0.58, 0.21],
                    [0.33, 0.17, 0.33]]

Step 4: weights · V → weighted combination of value vectors
```

Row 2 shows "cat" attends heavily to itself (0.58) — this is how the model learns which tokens are relevant to each other.

## Multi-Head Attention

Instead of one attention function, run **h parallel heads** (GPT-3 uses h=96). Each head learns different relationships (syntactic, semantic, positional). Outputs are concatenated and projected:

```
MultiHead(Q, K, V) = Concat(head₁, ..., headₕ) · W_O
```

## Positional Encoding

Self-attention is permutation-invariant — it has no notion of token order. Position information must be injected:

| Method | Used By | Key Property |
|--------|---------|-------------|
| Sinusoidal | Original Transformer | Fixed, based on sin/cos functions |
| Learned | GPT-1, GPT-2 | Trainable position embeddings |
| RoPE (Rotary) | Llama, DeepSeek, most modern LLMs | Encodes relative positions, supports length extrapolation |
| ALiBi | BLOOM | Adds linear bias to attention scores based on distance |

## Architecture Variants

| Type | Attention | Examples | Best For |
|------|-----------|----------|----------|
| **Encoder-only** | Bidirectional (sees full input) | BERT, RoBERTa | Classification, NER, embedding |
| **Decoder-only** | Causal (sees only past tokens) | GPT, Llama, Claude | Text generation, chat, code |
| **Encoder-Decoder** | Encoder bidirectional + decoder causal | T5, BART | Translation, summarization |

Modern LLMs are overwhelmingly **decoder-only**. The causal mask ensures each token can only attend to previous tokens — this is what makes autoregressive generation possible.

---

# Training Pipeline

LLM training is a multi-stage process:

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Pre-training    │───▶│       SFT        │───▶│    Alignment     │
│                   │    │                   │    │                  │
│ Next-token pred.  │    │ Instruction       │    │ RLHF or DPO     │
│ on massive corpus │    │ following         │    │                  │
│                   │    │                   │    │ Human preference │
│ Trillions of      │    │ ~100K curated     │    │ optimization     │
│ tokens            │    │ examples          │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
     Base model           Instruction model        Aligned model
     (completion)          (chat-capable)           (safe, helpful)
```

## Stage 1: Pre-training

The most expensive stage. The model learns language by predicting the next token on massive internet corpora.

- **Objective**: Next-token prediction (decoder-only) or masked language modeling (encoder-only, e.g., BERT masks ~15% of tokens)
- **Data**: Web crawls, books, code, academic papers — trillions of tokens
- **Compute**: Thousands of GPUs for weeks to months

## Stage 2: Supervised Fine-Tuning (SFT)

Train on curated (instruction, response) pairs written by humans. This teaches the model to:
- Follow instructions
- Adopt a conversational style
- Refuse harmful requests

Typically thousands to hundreds of thousands of high-quality examples. Quality matters far more than quantity.

## Stage 3: Alignment (RLHF / DPO)

Make the model's outputs align with human preferences — helpful, harmless, honest.

**RLHF (Reinforcement Learning from Human Feedback)**:
1. Collect human preference data (rank multiple model outputs)
2. Train a **Reward Model** on those preferences
3. Optimize the LLM via PPO (Proximal Policy Optimization) against the reward model

**DPO (Direct Preference Optimization)**:
- Skips the reward model entirely — optimizes directly on preference pairs
- Simpler, more stable, 40-75% less compute than RLHF
- Now the dominant approach (used by Meta for Llama 3/4)

## Training Cost

| Model | Params | Training Tokens | Estimated Cost | Compute |
|-------|--------|----------------|---------------|---------|
| GPT-3 | 175B | 300B | ~$4.6M | 355 GPU-years |
| Llama 3 | 405B | 15T | ~$30M+ | ~5.4×10²⁵ FLOPs |
| DeepSeek-V3 | 671B (37B active) | 14.8T | ~$5.6M (compute only) | 2048 H800 GPUs |
| GPT-4 | Undisclosed | Undisclosed | $78-100M+ | ~2.1×10²⁵ FLOPs |

## Scaling Laws (Chinchilla, 2022)

DeepMind's key finding: for a given compute budget, **model size and training tokens should be scaled equally**. The optimal ratio is ~20 tokens per parameter.

```
GPT-3:      175B params × 300B tokens  → ~1.7 tokens/param  (undertrained!)
Chinchilla:  70B params × 1.4T tokens  → ~20  tokens/param  (optimal)
Result: Chinchilla matched GPT-3 performance with 4× fewer parameters
```

This shifted the field from "bigger model" to "more data + right-sized model."

---

# Core Concepts

## Tokenization

LLMs don't process raw text — they work with **tokens** (subword units).

```
"unhappiness" → ["un", "happiness"]     (BPE might split it this way)
"ChatGPT"     → ["Chat", "G", "PT"]
"123456"      → ["123", "456"]           (why LLMs struggle with arithmetic)
```

| Method | Used By | How It Works |
|--------|---------|-------------|
| **BPE** (Byte Pair Encoding) | GPT series | Iteratively merge most frequent byte pairs |
| **SentencePiece** | Llama, T5 | Language-agnostic, treats input as raw bytes |
| **tiktoken** | OpenAI models | Optimized BPE implementation |

Typical vocab size: 32K–128K tokens. Tokenization directly affects API cost (you pay per token) and model capabilities (tokenization artifacts cause spelling/math issues).

## Context Window

The maximum number of tokens (input + output) the model processes in one pass.

| Model | Context Window |
|-------|---------------|
| GPT-3 (original) | 2K |
| GPT-3.5 Turbo | 16K |
| GPT-4 Turbo | 128K |
| GPT-4.1 | 1M |
| Claude Opus 4.6 | 1M |
| Gemini 1.5 Pro | 1M (up to 2M) |
| Llama 4 Scout | 10M |

Longer context ≠ better comprehension. Models often struggle with information in the **middle** of long contexts ("lost in the middle" problem).

## Sampling Parameters

When generating text, these parameters control the randomness/diversity of output:

**Temperature (T)**:
```
T = 0.0  → deterministic (greedy), always pick the top token
T = 0.7  → balanced creativity (common default)
T = 1.5  → high randomness, more creative but less coherent
```

**Top-p (nucleus sampling)**: Only consider tokens whose cumulative probability reaches p.
```
Top-p = 0.1  → very focused (top 10% probability mass)
Top-p = 0.9  → broad (top 90% probability mass)
```

**Top-k**: Only consider the k most probable tokens.

General advice: adjust temperature **or** top-p, not both simultaneously.

## In-Context Learning

LLMs can learn tasks from examples provided in the prompt — no weight updates needed:

```
Zero-shot:   "Translate to French: Hello"
One-shot:    "English: Good morning → French: Bonjour\nEnglish: Hello → French:"
Few-shot:    (provide 3-5 examples)
```

## Chain-of-Thought (CoT)

Prompting the model to show step-by-step reasoning dramatically improves performance on math, logic, and multi-step tasks:

```
Q: If a train travels 120 km in 2 hours, what is its speed?
A: Let me think step by step.
   Distance = 120 km
   Time = 2 hours
   Speed = Distance / Time = 120 / 2 = 60 km/h
```

---

# Key Models Comparison

| Model | Org | Release | Parameters | Context | Notes |
|-------|-----|---------|-----------|---------|-------|
| GPT-3.5 Turbo | OpenAI | Mar 2023 | Undisclosed | 16K | First widely used chat model |
| GPT-4 | OpenAI | Mar 2023 | Undisclosed (rumored MoE) | 128K | Major quality leap |
| GPT-4o | OpenAI | May 2024 | Undisclosed | 128K | Native multimodal |
| GPT-4.1 | OpenAI | Apr 2025 | Undisclosed | 1M | Coding-focused |
| Claude 3 Opus | Anthropic | Mar 2024 | Undisclosed | 200K | Strong reasoning |
| Claude 3.5 Sonnet | Anthropic | Jun 2024 | Undisclosed | 200K | Best code at the time |
| Claude Opus 4.6 | Anthropic | Feb 2026 | Undisclosed | 1M | Frontier reasoning + code |
| Gemini 1.5 Pro | Google | Feb 2024 | Undisclosed (MoE) | 1M-2M | Longest context window |
| Gemini 2.5 Pro | Google | Jun 2025 | Undisclosed (MoE) | 1M | Multimodal, strong reasoning |
| Llama 3 | Meta | Apr 2024 | 8B-405B | 128K | Open-weight |
| Llama 4 Scout | Meta | Apr 2025 | 109B (17B active, MoE) | 10M | Open-weight, huge context |
| DeepSeek-V3 | DeepSeek | Dec 2024 | 671B (37B active, MoE) | 128K | Remarkably cost-efficient |
| DeepSeek-R1 | DeepSeek | Jan 2025 | 671B (37B active, MoE) | 128K | Reasoning-specialized |

**MoE (Mixture of Experts)**: Only a subset of parameters are active per token. DeepSeek-V3 has 671B total params but only 37B active — this dramatically reduces inference cost while maintaining quality.

---

# Inference Optimization

LLM inference is **memory-bandwidth bound**, not compute-bound. The GPU has spare compute capacity but is bottlenecked reading weights and KV cache from memory. Most optimizations target this bottleneck.

## Key Techniques

| Technique | What It Optimizes | Typical Speedup | Trade-off |
|-----------|------------------|----------------|-----------|
| **KV Cache** | Avoids recomputing attention for past tokens | Essential (not optional) | Memory grows linearly with seq length |
| **Quantization** (INT8/INT4) | Reduces model size and memory bandwidth | 2-4× memory reduction | Slight accuracy loss (esp. INT4) |
| **Flash Attention** | Optimizes attention memory I/O via tiling | 2-4× attention speedup | None (exact computation) |
| **Speculative Decoding** | Uses small draft model to propose tokens | 2-3× generation speed | Needs a good draft model |
| **PagedAttention (vLLM)** | Manages KV cache like virtual memory | Higher throughput (2-4×) | Implementation complexity |
| **Continuous Batching** | Dynamically batches requests | Higher GPU utilization | Added scheduling logic |

## KV Cache

During autoregressive generation, each new token needs the Key and Value vectors of all previous tokens. Without caching, you'd recompute them every step.

```
Step 1: Generate token 1 → store K₁, V₁
Step 2: Generate token 2 → store K₂, V₂ (reuse K₁, V₁)
Step 3: Generate token 3 → store K₃, V₃ (reuse K₁,V₁, K₂,V₂)
...

Memory cost = seq_length × num_layers × 2 × hidden_dim × precision_bytes
```

For a 70B model with 128K context at FP16: ~40 GB of KV cache alone.

## Quantization

Reduce weight precision to shrink memory footprint:

```
FP32 (32 bits) → FP16 (16 bits) → INT8 (8 bits) → INT4 (4 bits)
  Full precision    Standard          2× smaller       4× smaller
```

- **INT8 (e.g., LLM.int8())**: Minimal quality loss, widely used in production
- **INT4 (GPTQ, AWQ)**: Some quality degradation, useful for running large models on consumer GPUs
- A 70B parameter model: FP16 = ~140 GB, INT8 = ~70 GB, INT4 = ~35 GB

## Speculative Decoding

Pair a small "draft" model (10-50× smaller) with the target LLM:

```
Draft model (fast): proposes tokens  [t₁, t₂, t₃, t₄, t₅]
                                         ↓
Target model (slow): verifies all 5 in ONE forward pass
                                         ↓
Result: accepts [t₁, t₂, t₃] ✓, rejects t₄ ✗
         → generated 3 tokens in ~1 forward pass instead of 3
```

Mathematically lossless — accepted tokens are identical to what the target model would have produced. Achieves 2-3× speedup when acceptance rate ≥ 0.6.

## PagedAttention (vLLM)

Manages KV cache like an OS manages virtual memory:

```
Traditional: contiguous pre-allocated KV cache → fragmentation, waste
PagedAttention: fixed-size blocks, non-contiguous → no fragmentation

┌────┐ ┌────┐ ┌────┐ ┌────┐
│Req1│ │Req2│ │Req1│ │Req3│  ← blocks from different requests
│Blk0│ │Blk0│ │Blk1│ │Blk0│    can be interleaved in GPU memory
└────┘ └────┘ └────┘ └────┘
```

This eliminates memory waste (traditional approaches waste 60-80% of KV cache memory) and enables serving many more concurrent requests.

---

# Practical Usage

## API Usage Pattern

Most LLM providers expose a similar chat completion API:

```shell
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6-20250514",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Explain KV cache in one sentence."}
    ]
  }'
```

Streaming responses use Server-Sent Events (SSE) for real-time token delivery.

## Prompt Engineering Basics

| Technique | When to Use | Example |
|-----------|------------|---------|
| **System prompt** | Set behavior/persona/constraints | "You are a Go expert. Be concise." |
| **Few-shot** | Demonstrate desired format | Provide 2-3 input→output examples |
| **Chain-of-thought** | Math, logic, multi-step tasks | "Think step by step" |
| **Structured output** | Need parseable response | "Respond in JSON with fields: ..." |

## RAG (Retrieval-Augmented Generation)

Augment the LLM with external knowledge to reduce hallucination and stay up-to-date:

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐
│ Documents │───▶│ Chunk + Embed│───▶│  Vector DB   │
└──────────┘    └──────────────┘    └──────────────┘
                                           │
                    User Query             │ semantic search
                        │                  │
                        ▼                  ▼
                 ┌─────────────────────────────┐
                 │  Combine query + retrieved   │
                 │  chunks into prompt          │
                 └──────────────┬──────────────┘
                                │
                                ▼
                         ┌────────────┐
                         │    LLM     │ → grounded response
                         └────────────┘
```

**Key stages**:
1. **Ingestion**: chunk documents, generate embeddings, store in vector DB (e.g., Pinecone, Weaviate, pgvector)
2. **Retrieval**: embed user query, find top-k similar chunks via cosine similarity
3. **Augmentation**: inject retrieved chunks into the prompt as context
4. **Generation**: LLM generates a response grounded in the retrieved information

## Function Calling / Tool Use

LLMs can be trained to emit structured tool-call requests:

```
User: "What's the weather in Tokyo?"
         ↓
LLM output: {"tool": "get_weather", "args": {"city": "Tokyo"}}
         ↓
App executes tool → {"temp": 22, "condition": "sunny"}
         ↓
LLM: "It's 22°C and sunny in Tokyo."
```

This enables **AI agents** that can plan, act, and iterate — calling APIs, running code, querying databases.

---

# Limitations

**Hallucination**: LLMs generate plausible but factually incorrect information — fabricated citations, wrong dates, invented entities. This is arguably fundamental: the per-token compute budget is insufficient for guaranteed factual recall. Scaling alone will not eliminate it.

**Lost in the Middle**: Even with 1M+ token context windows, models struggle to retrieve information buried in the middle of long contexts. Information at the beginning and end gets disproportionate attention.

**Reasoning Failures**:
- **Reversal curse**: Can answer "A is B" but fails "B is A"
- Multi-step logical reasoning degrades as steps increase
- Arithmetic errors on large numbers (partly a tokenization artifact)
- Spatial reasoning remains weak

**Cost**: Frontier model training costs $50M-$100M+. API inference costs $2-15 per million tokens for flagship models. Fine-tuning and alignment add significant overhead.

---

# References

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Vaswani et al., 2017 (original Transformer paper)
- [Training Compute-Optimal LLMs (Chinchilla)](https://arxiv.org/abs/2203.15556) — Hoffmann et al., 2022
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) — Jay Alammar
- [Understanding Encoder and Decoder LLMs](https://magazine.sebastianraschka.com/p/understanding-encoder-and-decoder) — Sebastian Raschka
- [State of LLMs 2025](https://magazine.sebastianraschka.com/p/state-of-llms-2025) — Sebastian Raschka
- [New LLM Pre-training and Post-training Paradigms](https://sebastianraschka.com/blog/2024/new-llm-pre-training-and-post-training.html)
- [vLLM: PagedAttention](https://github.com/vllm-project/vllm)
- [Speculative Decoding Introduction](https://developer.nvidia.com/blog/an-introduction-to-speculative-decoding-for-reducing-latency-in-ai-inference/) — NVIDIA
- [LLM Settings: Temperature, Top-p](https://www.promptingguide.ai/introduction/settings) — Prompt Engineering Guide
- [RAG Guide](https://www.promptingguide.ai/techniques/rag) — Prompt Engineering Guide

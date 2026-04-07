---
title: "LLM Fundamentals"
date: "2026-04-04T00:08:50+0800"
tags: ["llm", "AI"]
description: "Understanding LLM fundamentals — tokenization, embedding, attention, and text generation with concrete examples"
draft: true
---

> This post uses many abbreviations (BPE, FFN, RoPE, etc.). See the [LLM Abbreviations Glossary]({{< ref "/posts/llm/abbreviations" >}}) for a quick reference.

# What is LLM?

At its core, LLM is a **next-token predictor**.

Given a sequence of tokens, it predicts the most probable next token. By repeating this (autoregressive generation), it produces coherent text.

```
Input:  "The cat sat on the"
Model:  P("mat")=0.23, P("floor")=0.18, P("roof")=0.07, ...
Pick:   "mat"
```

Here's the high-level pipeline — every concept in this post maps to one of these stages:

```
"The cat sat"          ← raw text
     │
     ▼
[The] [cat] [sat]      ← Tokenization (§1)
     │
     ▼
[0.12, -0.5, ...]      ← Token Embedding (§2)
[0.78,  0.3, ...]
[0.45, -0.1, ...]
     │
     ▼
┌─────────────────┐
│   Transformer    │    ← Self-Attention (§3) + FFN (Feed-Forward Network) (§4)
│   × N layers     │
└────────┬────────┘
         │
         ▼
[0.01, 0.23, 0.18..]   ← Logits → Probabilities
         │
         ▼
      "on"              ← Sampling (§5)
```

## NLP (Natural Language Processing) Evolution

| Era | Period | Approach | Limitation |
|-----|--------|----------|-----------|
| Rule-based | 1950s-1980s | Hand-crafted patterns (ELIZA) | Can't generalize |
| Statistical | 1990s-2000s | N-grams, HMMs (Hidden Markov Models) | Sparse, no long-range context |
| Embeddings | 2013 | Word2Vec, GloVe | Static (one vector per word regardless of context) |
| Seq2Seq (Sequence-to-Sequence) | 2014-2017 | RNN (Recurrent Neural Network) / LSTM (Long Short-Term Memory) + attention | Sequential, slow, vanishing gradients |
| Transformer | 2017 | Self-attention, parallelizable | **The breakthrough** → modern LLMs |

## Where Does the Transformer Come From?

```
Machine Learning (ML)
  └── Deep Learning (DL)          ← ML with multi-layer neural networks
        └── Neural Network (NN)   ← inspired by biological neurons
              ├── CNN (Convolutional Neural Network)   ← images
              ├── RNN (Recurrent Neural Network)       ← sequences (text, audio)
              │     └── LSTM / GRU                     ← better at long sequences
              └── Transformer                          ← replaced RNN for NLP (2017)
                    └── LLM (Large Language Model)     ← Transformer at massive scale
```

1. **Machine Learning**: algorithms that learn patterns from data (instead of hand-coded rules)
2. **Deep Learning**: ML using neural networks with many layers — "deep" = many layers
3. **Neural Network**: layers of interconnected nodes, loosely inspired by brain neurons. Each node applies: `output = activation(weights · input + bias)`
4. **Transformer**: a specific neural network architecture from the 2017 paper ["Attention Is All You Need"](https://arxiv.org/abs/1706.03762). Replaced RNNs by using **self-attention** instead of sequential processing — this made it parallelizable and far more scalable
5. **LLM**: a Transformer trained on massive text data (billions to trillions of tokens) with billions of parameters

---

# 1. Tokenization

LLMs don't read characters or words — they read **tokens** (subword units).

## Why Not Characters or Words?

| Strategy | Vocabulary Size | Problem |
|----------|----------------|---------|
| Characters | ~256 | Sequences too long, no semantic meaning per unit |
| Words | ~500K+ | Vocabulary explodes, can't handle typos or new words |
| **Subwords (BPE, Byte Pair Encoding)** | **32K-128K** | **Best trade-off: manageable vocab, handles unseen words** |

## BPE (Byte Pair Encoding) — Step by Step

BPE builds a vocabulary by iteratively merging the most frequent character pairs. The result is a **vocabulary table** that maps each subword to an integer ID.

**Step 1 — Build the vocabulary** (done once, during tokenizer training):

Training corpus: `"low lower lowest lowly"`

```
Iteration 0: Start with characters
  l o w _ l o w e r _ l o w e s t _ l o w l y

Iteration 1: Most frequent pair: (l, o) → merge into "lo"
  lo w _ lo w e r _ lo w e s t _ lo w l y

Iteration 2: Most frequent pair: (lo, w) → merge into "low"
  low _ low e r _ low e s t _ low l y

Iteration 3: Most frequent pair: (low, e) → merge into "lowe"
  low _ lowe r _ lowe s t _ low l y

... continue until vocabulary size is reached
```

This produces a vocabulary — every character and merged subword gets an integer ID:
```
ID:     0    1    2    3    4    5    6    7    8    9    10     11
Token: "l"  "o"  "w"  "e"  "r"  "s"  "t"  "y"  "_"  "lo"  "low"  "lowe"
```

**Step 2 — Tokenize input** (done every time text is fed to the model):

Apply the learned merge rules to split input text into known subwords, then look up their IDs:

```
"lowest"  → ["lowe", "s", "t"]  → IDs: [11, 5, 6]
             ↑ in vocab  ↑ "st" not in vocab, falls back to "s"=5 + "t"=6

"lowly"   → ["low", "l", "y"]  → IDs: [10, 0, 7]
             ↑ in vocab  ↑ "ly" not in vocab, falls back to "l"=0 + "y"=7

"low"     → ["low"]           → IDs: [10]
             ↑ exact match
```

The key rule: if a subword isn't in the vocabulary, BPE **falls back to smaller known pieces**, all the way down to individual characters (which are always in the vocab).

> In real tokenizers the vocabulary is much larger (32K-128K entries), built from massive training corpora instead of 4 words. Subwords like "ness", "ing", "tion" would all be merged and have their own IDs.

The **output of tokenization is always a 1D array of integer IDs** — this is what the model receives:

```
"The cat sat on" → ["The", " cat", " sat", " on"] → [464, 2368, 3520, 319]
                    human-readable tokens             actual model input
```

## Tokenization Artifacts

This is why LLMs make surprising mistakes:

```
"strawberry" → ["straw", "berry"]       Can't easily count letters — "r" is split across tokens
"123 + 456"  → ["123", " +", " 456"]    Digits grouped arbitrarily → arithmetic errors
"GPT"        → ["G", "PT"]              Acronyms split unpredictably
```

📚 **References**:
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) by Andrej Karpathy — full implementation walk-through
- [Tiktokenizer](https://tiktokenizer.vercel.app/) — interactive tool to see how text gets tokenized
- [SentencePiece](https://github.com/google/sentencepiece) — language-agnostic tokenizer used by Llama, T5

---

# 2. Token Embedding

After tokenization, each token is a discrete ID (e.g., "cat" → 2368). But neural networks need continuous vectors. **Embedding** maps each token ID to a dense vector.

## How It Works

The model has a learned **embedding matrix** `E` of shape `[vocab_size × d_model]`. Each row is a token's embedding.

```
Vocabulary:    "the"=0  "cat"=1  "sat"=2  "on"=3  ...
               ┌                              ┐
Embedding      │  0.12  -0.50   0.33   0.78   │  ← "the" (ID 0)
Matrix E =     │  0.78   0.30  -0.12   0.45   │  ← "cat" (ID 1)
(vocab × d)    │  0.45  -0.10   0.67  -0.23   │  ← "sat" (ID 2)
               │  0.33   0.89   0.11   0.56   │  ← "on"  (ID 3)
               │  ...                          │
               └                              ┘

Input: "the cat sat" → IDs: [0, 1, 2]

Lookup: E[0] = [0.12, -0.50, 0.33, 0.78]   ← embedding for "the"
        E[1] = [0.78,  0.30, -0.12, 0.45]   ← embedding for "cat"
        E[2] = [0.45, -0.10, 0.67, -0.23]   ← embedding for "sat"
```

This is just a **table lookup**, not a computation.

## Where Do These Vectors Come From?

The embedding matrix is **randomly initialized** before training, then **learned via backpropagation** — the same way all other weights in the model are updated.

```
Before training:  E["the"] = [0.52, -0.11, 0.87, 0.03]   ← random initialization
After training:   E["the"] = [0.12, -0.50, 0.33, 0.78]   ← learned from data
```

During training, the model's goal is to predict the next token. If adjusting `E["the"]` helps the model make better predictions, backpropagation will nudge those values accordingly. After billions of training examples, the vectors converge to encode meaningful patterns about each token's usage.

## Why Embeddings Work

As a result, tokens that appear in similar contexts end up with **similar vectors**. This creates a semantic space:

```
cosine_similarity("king", "queen")  ≈ 0.85   (both royalty)
cosine_similarity("king", "pizza")  ≈ 0.12   (unrelated)
cosine_similarity("cat",  "dog")    ≈ 0.78   (both pets)
```

The famous example: `vector("king") - vector("man") + vector("woman") ≈ vector("queen")`

In real models, d_model is large: GPT-3 uses 12288 dimensions, Llama 3 (405B) uses 16384.

## Positional Encoding

Self-attention treats input as a **set** — it has no notion of token order. "cat sat on mat" and "mat on sat cat" would produce the same attention scores. We must inject position information.

```
Final input = Token Embedding + Positional Encoding

Token "cat" at position 2:
  token_emb  = [0.78,  0.30, -0.12,  0.45]    ← what the token is
  pos_enc(2) = [0.91, -0.42,  0.14, -0.99]    ← where the token is
  input      = [1.69, -0.12,  0.02, -0.54]    ← sum
```

| Method | How It Works | Used By |
|--------|-------------|---------|
| Sinusoidal | Fixed sin/cos functions at different frequencies | Original Transformer (2017) |
| Learned | Trainable position vectors (one per position) | GPT-1, GPT-2 |
| RoPE (Rotary Position Embedding) | Rotates Q/K vectors by position-dependent angle | Llama, DeepSeek, most modern LLMs |

RoPE is dominant today because it encodes **relative** positions (distance between tokens matters more than absolute position) and supports extrapolation to longer sequences than seen in training.

📚 **References**:
- [The Illustrated Word2Vec](https://jalammar.github.io/illustrated-word2vec/) by Jay Alammar — visual intuition for embeddings
- [Word Embeddings](https://lena-voita.github.io/nlp_course/word_embeddings.html) by Lena Voita — beginner-friendly course
- [RoPE explanation](https://blog.eleuther.ai/rotary-embeddings/) by EleutherAI — technical deep dive into Rotary Position Embeddings

---

# 3. Self-Attention

This is the core mechanism that makes Transformers work. It lets each token decide **how much to attend to every other token** in the sequence.

## Intuition

Consider: "The **animal** didn't cross the street because **it** was too tired."

What does "it" refer to? A human instantly knows "it" = "animal". Self-attention learns this by letting "it" compute a high attention score with "animal".

## Q, K, V — Query, Key, Value

Each token is projected into three vectors via learned weight matrices:

| Vector | Role | Analogy |
|--------|------|---------|
| **Q** (Query) | "What am I looking for?" | A search query |
| **K** (Key) | "What do I contain?" | A document title / tag |
| **V** (Value) | "What information do I provide?" | The actual document content |

```
For each token:
  Q = token_embedding × W_Q     (W_Q is a learned weight matrix)
  K = token_embedding × W_K
  V = token_embedding × W_V
```

## Dry Run — 3 Tokens, d_k = 4

Input: `["The", "cat", "sat"]`

**Step 1**: Project into Q, K, V (via learned weights — simplified here):

```
Q = [[1, 0, 1, 0],    K = [[1, 1, 0, 0],    V = [[1, 0, 1, 0],
     [0, 1, 0, 1],         [0, 0, 1, 1],         [0, 1, 0, 1],
     [1, 1, 0, 0]]         [1, 0, 1, 0]]         [1, 1, 0, 0]]
```

**Step 2**: Compute attention scores = Q · Kᵀ

```
Q · Kᵀ = [[1×1+0×1+1×0+0×0, 1×0+0×0+1×1+0×1, 1×1+0×0+1×1+0×0],   [[1, 1, 2],
           [0×1+1×1+0×0+1×0, 0×0+1×0+0×1+1×1, 0×1+1×0+0×1+1×0],  = [1, 1, 0],
           [1×1+1×1+0×0+0×0, 1×0+1×0+0×1+0×1, 1×1+1×0+0×1+0×0]]    [2, 0, 1]]
```

**Step 3**: Scale by √d_k = √4 = 2 (prevents softmax saturation)

```
Scaled = [[0.5, 0.5, 1.0],
          [0.5, 0.5, 0.0],
          [1.0, 0.0, 0.5]]
```

**Step 4**: Softmax (each row sums to 1.0)

```
Weights = [[0.27, 0.27, 0.45],    ← "The" attends most to "sat"
           [0.38, 0.38, 0.23],    ← "cat" attends equally to "The" and itself
           [0.51, 0.19, 0.31]]    ← "sat" attends most to "The"
```

**Step 5**: Weighted sum of V vectors

```
Output[0] = 0.27×V["The"] + 0.27×V["cat"] + 0.45×V["sat"]
          = 0.27×[1,0,1,0] + 0.27×[0,1,0,1] + 0.45×[1,1,0,0]
          = [0.72, 0.72, 0.27, 0.27]
```

Each output token is now a **context-aware blend** of all tokens, weighted by relevance.

## Multi-Head Attention

Instead of one attention, run **h parallel attention heads** (GPT-3: h=96, Llama 3 8B: h=32). Each head has its own W_Q, W_K, W_V — they learn different relationships:

```
Head 1: might learn syntactic structure    ("sat" → "cat" as subject)
Head 2: might learn positional proximity   ("sat" → "on" as next word)
Head 3: might learn semantic similarity    ("cat" → "animal")
...

MultiHead = Concat(head_1, ..., head_h) × W_O
```

## Causal Mask (Decoder-Only)

For text generation, a token must NOT attend to future tokens (it hasn't generated them yet). The causal mask enforces this:

```
              The  cat  sat  on
    The     [  ✓    ✗    ✗   ✗  ]     ✓ = can attend
    cat     [  ✓    ✓    ✗   ✗  ]     ✗ = masked (-∞ before softmax)
    sat     [  ✓    ✓    ✓   ✗  ]
    on      [  ✓    ✓    ✓   ✓  ]

Applied by setting masked positions to -∞ before softmax → they become 0 probability.
```

📚 **References**:
- [Attention? Attention!](https://lilianweng.github.io/posts/2018-06-24-attention/) by Lilian Weng — evolution of attention mechanisms
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) by Jay Alammar — the best visual explanation
- [Visual intro to Transformers](https://www.youtube.com/watch?v=wjZofJX0v4M) by 3Blue1Brown — animated explanation
- [LLM Visualization](https://bbycroft.net/llm) by Brendan Bycroft — interactive 3D visualization

---

# 4. Transformer Block

A single Transformer block does **one round of "gather context, then think"**:
- **Attention**: "which tokens are relevant to each other?" (gather context)
- **FFN**: "given that context, what knowledge applies here?" (think and refine)

But one round isn't enough — just like you can't fully understand a complex sentence in one pass. So LLMs **stack many blocks** (GPT-3: 96, Llama 3 8B: 32, Llama 3 405B: 126), each refining the token representations further:

```
Input: "The bank by the river was steep"

Block 1-2:    syntax     — "bank" is a noun, "was" links to "bank"
Block 3-10:   semantics  — "bank" + "river" → this means riverbank, not financial bank
Block 11-30:  reasoning  — combines all context to predict what comes next
```

After block 1, the vector for "bank" still mostly means "bank (ambiguous)". After block 10, it means "riverbank" — because attention pulled in context from "river", and the FFN transformed that blended signal into a more specific representation.

Here's one block:

```
         Input (embeddings)
              │
              ▼
    ┌───────────────────┐
    │  Multi-Head        │
    │  Self-Attention     │  ← "which tokens are relevant to each other?"
    └─────────┬──────────┘
              │
         ┌────▼────┐
         │  Add &   │  ← residual connection: output = attention(x) + x
         │ LayerNorm│    prevents vanishing gradients in deep networks
         └────┬─────┘
              │
    ┌─────────▼──────────┐
    │  FFN (Feed-Forward   │
    │       Network)      │  ← "what to do with that information?"
    │                     │
    │  up = x × W₁       │  d_model → 4×d_model (expand)
    │  act = GeLU(up)     │  GeLU (Gaussian Error Linear Unit) non-linearity
    │  down = act × W₂   │  4×d_model → d_model (compress)
    └─────────┬──────────┘
              │
         ┌────▼────┐
         │  Add &   │  ← another residual connection
         │ LayerNorm│
         └────┬─────┘
              │
              ▼
         Output (to next layer)
```

## Attention vs FFN: Who Does What?

Think of it as a **team meeting**:
- **Attention** = the discussion phase — everyone shares information, and each person decides who to listen to. It operates **across tokens** (token-to-token communication).
- **FFN** = the thinking phase — each person goes back to their desk and processes what they heard, using their own knowledge. It operates **within each token independently** (no cross-token communication).

Concrete example with `"Paris is the capital of ___"`:

```
After Attention:
  The vector for "___" now contains blended information from
  "Paris", "capital", "of" — it knows the context.

After FFN:
  The FFN processes that blended vector and activates the
  stored knowledge: "capital of Paris → France"
  The vector for "___" is now transformed to strongly
  predict "France" as the next token.
```

| Component | Operates On | What It Does | Where Knowledge Lives |
|-----------|------------|-------------|----------------------|
| **Attention** | Between tokens | Routes and blends information | Learns **which** tokens matter to each other |
| **FFN** | Each token independently | Transforms and refines | Stores **factual knowledge** in its weight matrices |

The FFN's weight matrices (W₁, W₂) are enormous — they make up ~2/3 of the model's total parameters. Research shows that specific neurons in FFN layers fire for specific facts (e.g., "Paris → France"), which is why FFN is often called the model's "memory".

## Residual Connections

Without residuals, gradients vanish in deep networks (96+ layers). The residual path provides a "gradient highway":

```
output = LayerNorm(x + Sublayer(x))
                   ↑
                   gradient flows directly through here
```

## Architecture Variants

| Type | Attention Pattern | Examples | Best For |
|------|------------------|----------|----------|
| **Encoder-only** | Bidirectional (sees all tokens) | BERT (Bidirectional Encoder Representations from Transformers), RoBERTa | Classification, NER (Named Entity Recognition), embeddings |
| **Decoder-only** | Causal (sees only past tokens) | GPT (Generative Pre-trained Transformer), Llama, Claude | Text generation, chat, code |
| **Encoder-Decoder** | Encoder: bidirectional, Decoder: causal + cross-attention | T5, BART | Translation, summarization |

Modern LLMs are almost exclusively **decoder-only** — simpler, scales better, and the causal mask enables autoregressive generation.

📚 **References**:
- [nanoGPT](https://www.youtube.com/watch?v=kCc8FmEb1nY) by Andrej Karpathy — reimplement GPT from scratch in 2 hours
- [Transformer Circuits Thread](https://transformer-circuits.pub/) by Anthropic — deep analysis of what each component learns

---

# 5. Text Generation (Sampling)

After the final Transformer block, the model outputs a **logit** (raw score) for every token in the vocabulary. How we convert logits into a chosen token is the **sampling strategy**.

## From Logits to Probabilities

To keep the math verifiable, let's use a simplified vocabulary of just 4 tokens:

```
Tokens:  ["on", "the", "mat", "in"]
Logits:  [2.0,   1.0,   0.5,   0.0]      ← raw scores from the model

Softmax: P(token) = e^logit / Σe^all_logits

  e^2.0 = 7.39    e^1.0 = 2.72    e^0.5 = 1.65    e^0.0 = 1.00
  sum = 7.39 + 2.72 + 1.65 + 1.00 = 12.76

  P("on")  = 7.39 / 12.76 = 0.58
  P("the") = 2.72 / 12.76 = 0.21
  P("mat") = 1.65 / 12.76 = 0.13
  P("in")  = 1.00 / 12.76 = 0.08
                               sum = 1.00 ✓
```

> In real models, the softmax is over the entire vocabulary (32K-128K tokens), so each individual probability is much smaller. We use 4 tokens here to keep the math clear.

## Greedy Decoding

Always pick the highest probability token. Deterministic but often repetitive:

```
P("on")=0.58, P("the")=0.21, P("mat")=0.13, P("in")=0.08
→ Always picks "on"
```

## Temperature

Temperature **reshapes** the probability distribution before sampling:

```
New logits = original logits / T
```

| Temperature | Effect | Distribution |
|-------------|--------|-------------|
| T → 0 | Deterministic (greedy) | All probability on top token |
| T = 1.0 | Original distribution | Balanced |
| T > 1.0 | Flatter, more random | Spreads probability to unlikely tokens |

**Dry run** with logits `[2.0, 1.0, 0.5, 0.0]` for tokens `["on", "the", "mat", "in"]`:

```
T = 0.5 (focused):
  logits/T = [4.0, 2.0, 1.0, 0.0]
  e^4.0=54.60  e^2.0=7.39  e^1.0=2.72  e^0.0=1.00  sum=65.71
  softmax  → P("on")=0.83  P("the")=0.11  P("mat")=0.04  P("in")=0.02
  → almost always picks "on"

T = 1.0 (original):
  logits/T = [2.0, 1.0, 0.5, 0.0]
  softmax  → P("on")=0.58  P("the")=0.21  P("mat")=0.13  P("in")=0.08
  → usually "on", sometimes "the"

T = 2.0 (creative):
  logits/T = [1.0, 0.5, 0.25, 0.0]
  e^1.0=2.72  e^0.5=1.65  e^0.25=1.28  e^0.0=1.00  sum=6.65
  softmax  → P("on")=0.41  P("the")=0.25  P("mat")=0.19  P("in")=0.15
  → more diverse, might pick "mat" or "in"
```

Notice how temperature flattens or sharpens the distribution:
```
              "on"   "the"   "mat"   "in"
T = 0.5  →   0.83    0.11    0.04    0.02    ← concentrated
T = 1.0  →   0.58    0.21    0.13    0.08    ← balanced
T = 2.0  →   0.41    0.25    0.19    0.15    ← flattened
```

## Top-k Sampling

Only consider the **k most probable** tokens, then renormalize:

```
Original: P("on")=0.58, P("the")=0.21, P("mat")=0.13, P("in")=0.08

Top-k=2: keep only top 2, zero out the rest
  P("on")=0.58, P("the")=0.21 → renormalize (divide by 0.58+0.21=0.79):
  P("on")=0.73, P("the")=0.27
  → sample from these 2 only
```

Problem: top-k is **fixed**. If the model is very confident (top token is 0.95), k=50 still considers 50 tokens. If uncertain, k=2 might cut off good options.

## Top-p (Nucleus Sampling)

Keep the smallest set of tokens whose **cumulative probability** reaches p:

```
Sorted: P("on")=0.58, P("the")=0.21, P("mat")=0.13, P("in")=0.08

Top-p=0.7:
  "on"  → cumulative: 0.58 (< 0.7, keep)
  "the" → cumulative: 0.79 (≥ 0.7, keep this last one, stop)
  → sample from {"on", "the"} (2 tokens)

Top-p=0.95:
  "on"  → cumulative: 0.58 (< 0.95, keep)
  "the" → cumulative: 0.79 (< 0.95, keep)
  "mat" → cumulative: 0.92 (< 0.95, keep)
  "in"  → cumulative: 1.00 (≥ 0.95, keep this last one, stop)
  → sample from all 4 tokens
```

Top-p **adapts** — when the model is confident, fewer tokens pass the threshold; when uncertain, more do.

## Practical Advice

| Use Case | Recommended Settings |
|----------|---------------------|
| Code generation | T=0.0 (deterministic) or T=0.2, top-p=0.1 |
| Factual Q&A | T=0.3, top-p=0.3 |
| Creative writing | T=0.8-1.0, top-p=0.9 |
| Brainstorming | T=1.0-1.2, top-p=0.95 |

General rule: adjust **temperature or top-p**, not both. They do similar things and combining them can produce unpredictable results.

📚 **References**:
- [LLM Settings — Temperature, Top-p](https://www.promptingguide.ai/introduction/settings) by Prompt Engineering Guide
- [Decoding Strategies in LLMs](https://mlabonne.github.io/blog/posts/2023-06-07-Decoding_strategies.html) by Maxime Labonne — visual guide with code
- [How to generate text](https://huggingface.co/blog/how-to-generate) by Hugging Face — comprehensive sampling guide

---

# 6. Putting It All Together

Let's trace `"The cat sat"` through the entire pipeline to predict the next token:

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: TOKENIZE                                                │
│   "The cat sat" → ["The", "cat", "sat"] → IDs: [464, 2368, 3520]│
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: EMBED                                                   │
│   E[464]  = [0.12, -0.50, 0.33, ...]   (d=4096 in real models) │
│   E[2368] = [0.78,  0.30, -0.12, ...]                          │
│   E[3520] = [0.45, -0.10, 0.67, ...]                           │
│                                                                 │
│   + Positional Encoding (RoPE, Rotary Position Embedding)        │
│     → position-aware embeddings                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: TRANSFORMER × N layers                                  │
│                                                                 │
│   Layer 1:                                                      │
│     Attention: "sat" attends to "cat" (subject) and "The"       │
│     FFN (Feed-Forward Network): transforms each token's repr.   │
│                                                                 │
│   Layer 2-N:                                                    │
│     Builds increasingly abstract representations                │
│     Early layers: syntax  Middle: semantics  Late: task-level   │
│                                                                 │
│   Final representation for last token "sat":                    │
│     h = [1.34, -0.89, 2.11, 0.56, ...]                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: PROJECT TO VOCABULARY                                   │
│   logits = h × W_vocab    (4096 → 32000 vocabulary logits)      │
│                                                                 │
│   logits: ["on"=2.0, "the"=1.0, "mat"=0.5, "in"=0.0, ...]     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: SAMPLE                                                  │
│   softmax → P("on")=0.58, P("the")=0.21, P("mat")=0.13, ...   │
│   with T=1.0, top-p=0.9 → sample → "on"                        │
│                                                                 │
│   Append "on" to sequence → "The cat sat on"                    │
│   Repeat from Step 1 with new sequence...                       │
└─────────────────────────────────────────────────────────────────┘
```

This loop continues until:
- A special `<EOS>` (End of Sequence) token is generated
- A maximum length limit is reached
- The caller stops the generation

That's it. Every LLM — from GPT-4 to Llama to Claude — follows this same fundamental pipeline.

---

# What's Next

This post covered **how an LLM works internally** — the architecture. But building a useful LLM involves many more stages. Here's the full picture:

```
┌──────────────────────┐
│  1. Architecture      │  ← this post (fundamentals)
│  (Transformer)        │
└──────────┬───────────┘
           │ architecture is what gets trained
           ▼
┌──────────────────────┐
│  2. Pre-Training      │  ← train on massive data (next-token prediction)
│                       │    adjusts all the weights we discussed:
│                       │    embedding matrix, W_Q/W_K/W_V, FFN weights
└──────────┬───────────┘
           │ produces a base model (can complete text, but not chat)
           ▼
┌──────────────────────────────────────────────────────────┐
│  3-5. Post-Training (treats model mostly as a black box)  │
│                                                           │
│  3. Post-Training Datasets  — curate instruction data     │
│  4. SFT (Supervised Fine-Tuning) — teach it to chat       │
│  5. Preference Alignment (RLHF/DPO) — make it safe/helpful│
└──────────┬───────────────────────────────────────────────┘
           │ produces a chat model (e.g., ChatGPT, Claude)
           ▼
┌──────────────────────────────────────────────────────────┐
│  6-8. Ship & Improve (also treats model as a black box)   │
│                                                           │
│  6. Evaluation       — measure quality (benchmarks, human) │
│  7. Quantization     — compress for deployment (INT8/INT4) │
│  8. New Trends       — merging, multimodal, reasoning      │
└──────────────────────────────────────────────────────────┘
```

Steps 1 → 2 are tightly coupled — pre-training directly adjusts the weights inside the architecture we covered (embeddings, attention, FFN). But steps 3-8 largely treat the model as a black box: feed it data, train, evaluate, compress. You don't need to understand self-attention to do SFT or run benchmarks.

That said, the fundamentals help you understand **why** things work: why certain prompts are more effective (attention patterns), why models hallucinate (FFN knowledge retrieval limits), why quantization can degrade quality (weight precision matters for subtle knowledge stored in FFN).

---

# References

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Vaswani et al., 2017 (the original Transformer paper)
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) — Jay Alammar
- [Visual intro to Transformers](https://www.youtube.com/watch?v=wjZofJX0v4M) — 3Blue1Brown
- [LLM Visualization](https://bbycroft.net/llm) — Brendan Bycroft (interactive 3D)
- [nanoGPT](https://www.youtube.com/watch?v=kCc8FmEb1nY) — Andrej Karpathy (build GPT from scratch)
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) — Andrej Karpathy
- [Decoding Strategies in LLMs](https://mlabonne.github.io/blog/posts/2023-06-07-Decoding_strategies.html) — Maxime Labonne
- [Transformer Circuits Thread](https://transformer-circuits.pub/) — Anthropic
- [Understanding Encoder and Decoder LLMs](https://magazine.sebastianraschka.com/p/understanding-encoder-and-decoder) — Sebastian Raschka

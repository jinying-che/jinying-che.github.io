---
title: "LLM Abbreviations Glossary"
date: "2026-01-22T11:00:00+08:00"
tags: ["large language model"]
description: "common abbreviations used in the large language model domain"
draft: true
---

A quick reference for common abbreviations in the LLM (Large Language Model) domain.

# Training & Techniques

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **SFT** | Supervised Fine-Tuning | Training on curated question-answer pairs |
| **RL** | Reinforcement Learning | Learning by trial and reward signals |
| **RLHF** | Reinforcement Learning from Human Feedback | RL where humans rank outputs to guide training |
| **DPO** | Direct Preference Optimization | Simpler alternative to RLHF, no reward model needed |
| **GRPO** | Group Relative Policy Optimization | RL technique used in reasoning models (DeepSeek) |
| **PPO** | Proximal Policy Optimization | Popular RL algorithm for training LLMs |
| **LoRA** | Low-Rank Adaptation | Memory-efficient fine-tuning technique |
| **QLoRA** | Quantized LoRA | LoRA + 4-bit quantization for even less memory |

# Architecture & Models

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **LLM** | Large Language Model | The models like GPT, Claude, Llama |
| **NLP** | Natural Language Processing | Field of AI dealing with human language |
| **RNN** | Recurrent Neural Network | Older architecture before Transformers |
| **LSTM** | Long Short-Term Memory | Improved RNN that handles longer sequences |
| **GRU** | Gated Recurrent Unit | Simplified version of LSTM |
| **MLP** | Multilayer Perceptron | Basic fully-connected neural network |
| **GPT** | Generative Pre-trained Transformer | OpenAI's model architecture |
| **MoE** | Mixture of Experts | Architecture where only some "experts" activate per token |
| **MQA** | Multi-Query Attention | Attention optimization sharing key-value heads |
| **GQA** | Grouped-Query Attention | Middle ground between MHA and MQA |
| **MHA** | Multi-Head Attention | Standard attention with multiple heads |

# Applications & Deployment

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **RAG** | Retrieval-Augmented Generation | Combining LLMs with external knowledge retrieval |
| **API** | Application Programming Interface | Way to access LLMs over the internet |
| **VRAM** | Video Random Access Memory | GPU memory needed to run models |
| **MCP** | Model Context Protocol | Standard for connecting LLMs to external tools |
| **A2A** | Agent-to-Agent Protocol | Standard for agent interoperability |

# Evaluation & Benchmarks

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **MMLU** | Massive Multitask Language Understanding | Popular benchmark for testing LLMs |
| **CoT** | Chain-of-Thought | Prompting technique for step-by-step reasoning |
| **PRM** | Process Reward Model | Model that scores intermediate reasoning steps |

# Quantization & Optimization

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **GGUF** | GPT-Generated Unified Format | File format for quantized models (llama.cpp) |
| **GPTQ** | GPT Quantization | Post-training quantization method |
| **AWQ** | Activation-aware Weight Quantization | Quantization preserving important weights |
| **FP16** | 16-bit Floating Point | Half-precision number format |
| **FP32** | 32-bit Floating Point | Full-precision number format |
| **INT8** | 8-bit Integer | Low-precision integer format |

# Data & Preprocessing

| Abbreviation | Full Name | What It Is |
|--------------|-----------|------------|
| **BoW** | Bag-of-Words | Text representation ignoring word order |
| **TF-IDF** | Term Frequency-Inverse Document Frequency | Text weighting technique |

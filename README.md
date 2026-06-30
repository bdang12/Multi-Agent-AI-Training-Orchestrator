# 🤖 Multi-Agent AI Training Orchestrator

> A local Student–Teacher AI learning system for self-study, memory building, and synthetic dataset generation.

---

## 📌 1. Project Overview

This project is a local AI learning system that uses two AI roles:

- 🧑‍🎓 **Student AI:** runs locally on the user's computer using Ollama.
- 🧑‍🏫 **Teacher AI:** can be connected to a paid API such as OpenAI or Gemini.
- 🧠 **Python Orchestrator:** controls the learning flow, saves memory, journal notes, and draft datasets.

The main goal is to let a local Student AI ask questions, receive answers from a stronger Teacher AI, study the answer by itself, and save what it learned into files.

**Current Version:** `Version 1 — Terminal MVP`

---

## ✨ 2. Main Features

The current version supports:

- 📝 Student AI generates questions about a learning topic.
- 💬 Teacher AI gives an answer.
- 🔍 Student AI studies the Teacher's answer.
- 💾 The program saves learning results into:
  - `memory/`
  - `journal/`
  - `dataset/draft/`
- 🖥️ The program runs from the terminal.

---

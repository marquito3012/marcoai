# Marco AI - Implementation Plan & Progress

This document tracks the detailed steps for implementing the Marco AI project, adhering to the hardware constraints (Raspberry Pi 3, 1GB RAM) and the strategic technical decisions.

## 🛠️ Step 1: Lay the Foundation (Architecture & Decisions)
**Status:** ✅ **DONE**

**Goals:**
- Design a memory-efficient backend prioritizing low RAM usage.
- Establish a "Modular Monolith" architecture using FastAPI and SQLite.
- Create the core folder structure and database schema.

**Completed Items:**
- [x] Initialized `backend/` directory with modular `app/` structure.
- [x] Configured memory-efficient `FastAPI` settings (`config.py`).
- [x] Designed `SQLite` database schema with `sqlite-vec` support (`database.py`).
- [x] Set up Docker and `docker-compose.yml` with explicit memory limits.
- [x] Created `run_tests.sh` with virtual environment support to handle OS restrictions.

---

## 🧠 Step 2: Agent Brain & External Integrations
**Status:** ✅ **DONE**

**Goals:**
- Build the core orchestrator logic without relying on memory-heavy multi-agent swarms.
- Use a single-agent orchestrator with LLM Tool Calling to save time, API calls, and memory.
- Implement a robust tool registration system for executing specific Python functions mapping to core capabilities.

**Completed Items:**
- [x] Implemented `SyncReActOrchestrator` & `ReActOrchestrator` in `agent/orchestrator.py`.
- [x] Built the `ToolRegistry` singleton and elegant `@tool` decorator pattern in `agent/tools.py`.
- [x] Created robust tool functions for `calendar`, `finance`, `habits`, `shopping`, and `memory_search` (RAG).
- [x] Set up LLM failover logic favoring speed/cost (Groq -> OpenRouter -> Gemini).
- [x] Wrote and fixed the full test suite (`test_orchestrator.py` passes 31/31).

---

## 🎨 Step 3: Frontend Design (A Pro UX/UI)
**Status:** ✅ **DONE**

**Goals:**
- Design a user interface for a single-page dashboard.
- Theme: Minimalist, dark-themed, "personal dashboard" aesthetic.
- Key Sections: Calendar, Finance, Habits, Chat window.
- Constraint: It must render incredibly efficiently on the client-side to keep the Pi 3's backend lean.

**Completed Items:**
- [x] Generated design system using UI/UX Pro Max skill (dark fintech palette, glassmorphism, Fira Code/Fira Sans).
- [x] Created text-based wireframe layout (2-column CSS Grid: left cards + right chat).
- [x] Implemented `style.css` with full design tokens, glassmorphism effects, responsive breakpoints.
- [x] Built `index.html` with semantic HTML5, Lucide SVG icons, Google Fonts.
- [x] Built `app.js` with modular IIFE pattern (Chat, Calendar, Finance, Habits modules).
- [x] Updated `main.py` to serve static files via FastAPI `StaticFiles`.
- [x] Verified in browser — all cards render, icons load, layout correct.

---

## 🏗️ Step 4: Full Stack Implementation
**Status:** 🔄 **IN PROGRESS**

**Goals:**
- Execute the plans and tie everything together.
- Build the frontend static layer (originally specified as Vanilla JS; alternative: HTMX + Tailwind CSS).
- Connect the frontend securely to the FastAPI backend.

**Task Checklist:**
- [x] Complete the FastApi backend with database and tool logic.
- [x] Build the static frontend for max performance.
- [x] Assemble routing and connect the frontend HTTP calls to the backend.

---

## 🔧 Step 5: Iteration, Cleanup, and Best Practices
**Status:** 🔄 **ONGOING**

**Goals:**
- Systematic debugging using logs.
- Constant refactoring to reduce the memory footprint when idle.
- Maintain comprehensive Git commit messages explaining *why* changes are made.

**Current Notes/Completed Actions:**
- [x] Systematic debugging: Solved pytest operational errors caused by overlapping SQLite schemas.
- [x] Cleanup: Fixed Docker permission issues (`--chown`) and silenced global pip warnings in CI.
- [ ] Ongoing: Watch for memory leaks.
- [ ] Ongoing: Follow comprehensive commit messages.

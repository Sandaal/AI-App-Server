---
title: Walkthrough videos
---

# Walkthrough videos

Four short walkthroughs, one for each part of the feature tour. Each has a voice-over and captions. The terminal output in them comes from a real run: the server with a local model (Ollama, llama3.2:3b) on a laptop CPU.

The voice-over is computer-generated (offline text-to-speech). Features marked preview are built and tested on emulated hardware, and the videos say so; see [Project status](status.md).

## 1. Architecture (5:11)

One binary in place of Redis, Kafka, a vector database and an AI gateway; how a request flows; Raft clusters; open protocols; per-app isolation.

<video controls preload="none" width="100%" poster="../assets/videos/1-architecture-thumbnail.png">
  <source src="../assets/videos/1-architecture.mp4" type="video/mp4">
  <track kind="captions" src="../assets/videos/1-architecture.vtt" srclang="en" label="English">
</video>

[Download MP4](assets/videos/1-architecture.mp4) · [Captions (SRT)](assets/videos/1-architecture.srt)

## 2. Enterprise security (4:21)

Sign-in with Entra ID and OIDC, API keys with roles, encryption at rest, the audit log, guardrails blocking a prompt injection, and secrets in your vault.

<video controls preload="none" width="100%" poster="../assets/videos/2-security-thumbnail.png">
  <source src="../assets/videos/2-security.mp4" type="video/mp4">
  <track kind="captions" src="../assets/videos/2-security.vtt" srclang="en" label="English">
</video>

[Download MP4](assets/videos/2-security.mp4) · [Captions (SRT)](assets/videos/2-security.srt)

## 3. Hardware support (4:32)

CPU-only and offline, sizing to the machine, and the preview work on GPUs with vLLM, CXL memory, BlueField DPUs and confidential VMs.

<video controls preload="none" width="100%" poster="../assets/videos/3-hardware-thumbnail.png">
  <source src="../assets/videos/3-hardware.mp4" type="video/mp4">
  <track kind="captions" src="../assets/videos/3-hardware.vtt" srclang="en" label="English">
</video>

[Download MP4](assets/videos/3-hardware.mp4) · [Captions (SRT)](assets/videos/3-hardware.srt)

## 4. Time to market (3:22)

The ten ready-made apps, three commands to production, versions and rollback, tests and evaluations, and where it deploys.

<video controls preload="none" width="100%" poster="../assets/videos/4-time-to-market-thumbnail.png">
  <source src="../assets/videos/4-time-to-market.mp4" type="video/mp4">
  <track kind="captions" src="../assets/videos/4-time-to-market.vtt" srclang="en" label="English">
</video>

[Download MP4](assets/videos/4-time-to-market.mp4) · [Captions (SRT)](assets/videos/4-time-to-market.srt)

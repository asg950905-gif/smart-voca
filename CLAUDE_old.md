# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**smart-voca** is an AI-powered vocabulary learning agent. The project is structured around an AI agent system that helps users learn and master vocabulary interactively.

### Directory Structure

- **ai-agent/** - Core agent implementation and logic
  - **claude/** - Claude AI integration and API interactions
  - **uploads/** - User-uploaded content and learning materials
- **docs/** - Project documentation

## Development Commands

*(These should be updated once the project structure and build system are established)*

```bash
# Installation
npm install

# Development server
npm run dev

# Build
npm run build

# Tests
npm run test

# Lint
npm run lint

# Run a single test
npm run test -- <test-file>
```

## Architecture Decisions

### AI Agent Design
- Use Claude API for intelligent vocabulary assessment and personalized learning paths
- Implement a stateful agent system that tracks user progress and adapts difficulty
- Store learning sessions in uploads directory for user reference

### Key Considerations
- **User Data**: Be mindful of storing user progress and learning history securely
- **API Integration**: Claude API calls should be optimized and cached where possible to reduce latency
- **Session State**: Maintain conversation context across interactions for coherent learning experiences

## Common Tasks

- **Adding new vocabulary sets**: Place source material in `ai-agent/uploads/` and implement loader in core agent
- **Modifying learning logic**: Update agent prompts and assessment logic in `ai-agent/claude/`
- **Integration testing**: Test agent interactions end-to-end with sample vocabulary sets

---

**Next Steps**: Once the technology stack is selected (Node.js/Python, which framework, database choice), update this file with actual build commands and architecture details specific to the implementation.

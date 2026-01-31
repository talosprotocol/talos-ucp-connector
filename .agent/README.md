# Agent workspace: services/ucp-connector
> **Project**: services/ucp-connector

This folder contains agent-facing context, tasks, workflows, and planning artifacts for this submodule.

## Current State
UCP checkout lifecycle implementation with strict signing rules and locked security invariants. Reference merchant behavior exists or is staged.

## Expected State
Spec-complete lifecycle coverage, robust idempotency, and strong signature verification on all operations including GET.

## Behavior
Implements the UCP integration surface with ES256 signing, canonical payload rules, and strict request validation and auditing.

## How to work here
- Run/tests:
- Local dev:
- CI notes:

## Interfaces and dependencies
- Owned APIs/contracts:
- Depends on:
- Data stores/events (if any):

## Global context
See `.agent/context.md` for monorepo-wide invariants and architecture.

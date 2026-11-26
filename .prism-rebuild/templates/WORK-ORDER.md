# Work order: replace with a concrete outcome

Status: pending · Owner: assign one actor · Reviewer: assign a distinct actor when available

## Objective and scope

Describe the user-visible or operational problem in one paragraph, the behavior this task will establish, and the bounded scope. Link the exact requirement IDs and acceptance IDs. Identify the milestone and gate. Do not treat a work-order title or passed unit test as completion of every linked cross-domain scenario.

## Inputs and dependencies

Record the target repository/root, source commit or relevant artifact versions, contract/schema version, required predecessor work and applicable project instructions. List only the reference files needed for this task. Include the relevant original knowledge rules by ID when design judgment is involved.

## Ownership and authority

- Existing paths this worker may edit:
- New paths this worker may create:
- Read-only inputs:
- Shared files that need the integration owner's coordination:
- Allowed operations and relevant limits:
- Paid external design dispatch authority, if any:
- Expected model/capabilities and how the observed assignment will be recorded:

New outputs need not exist yet, but their nearest existing ancestor must be inside the authorized root and free of unsafe redirects. Do not claim ownership of the entire repository for a small task. A worker may propose a contract change; the integration owner resolves shared interfaces before dependent implementations diverge.

## Acceptance plan

For each acceptance ID, state the meaningful assertion, test location, actual command argv, environment/fixture and expected evidence. Include relevant failure, concurrency, cancellation or recovery cases. An expected failure inside a product test still requires the test command itself to exit zero after checking that failure.

## Implementation notes

Record the smallest coherent approach and any explicit decision needed before coding. Preserve existing useful security, compatibility and state behavior. Avoid unrelated cleanup and dependencies that do not resolve a measured need.

## Result and handoff

Return changed paths, behavior established, actual checks run, receipt/log/report paths, observed model assignment, unresolved findings, dependency changes and the next action. Distinguish implemented-unverified from verified. If blocked, identify the exact missing prerequisite and complete independent work first. Do not copy full logs into the director's context when an inspectable local path and a concise result suffice.

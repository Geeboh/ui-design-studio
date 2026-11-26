#!/usr/bin/env python3
"""Run a reviewed implementation verification plan; never infer missing evidence."""
from __future__ import annotations
import argparse
import os
import platform
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from prism_pack import PACK_ROOT, atomic_write, candidate_snapshot, canonical, digest, emit, file_digest, read_json, receipt_evidence_errors, repo_root, safe_child, stamp, state_path, write_json

def redact(text):
    for name, value in os.environ.items():
        if len(value) >= 8 and re.search(r"(TOKEN|SECRET|PASSWORD|API_KEY|CREDENTIAL)", name, re.I):
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)((?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text

def check_review(repo, plan, plan_sha, fingerprint, case_ids):
    spec = plan.get("review", {})
    path = safe_child(repo, spec.get("evidencePath", ""), must_exist=True)
    record = read_json(path)
    if record.get("sourceFingerprintSha256") != fingerprint or record.get("reviewedPlanSha256") != plan_sha:
        raise ValueError("Release review is not bound to this exact candidate and verification plan")
    reviewer = record.get("reviewer", {})
    identity = reviewer.get("identity")
    actor = reviewer.get("actorId")
    implementers = reviewer.get("implementationActorIds", [])
    if not identity or not actor or not isinstance(implementers, list) or not implementers:
        raise ValueError("Review must identify reviewer and implementation actors")
    independent = reviewer.get("independent") is True
    if independent:
        if actor in implementers or reviewer.get("method") != "independent":
            raise ValueError("Independent reviewer must have a distinct actor identity")
        recommendation = "ready"
    else:
        if reviewer.get("method") != "declared-sequential-fallback" or not reviewer.get("fallbackReason"):
            raise ValueError("Non-independent review requires an explicit sequential fallback method and reason")
        recommendation = "ready-with-disclosed-fallback"
    if spec.get("independent") is not independent or spec.get("reviewer") != identity:
        raise ValueError("Plan review identity/mode differs from review evidence")
    if record.get("findings", {}).get("severeOpen") != 0 or record.get("recommendation") != recommendation:
        raise ValueError("Review has unresolved severe findings or does not recommend readiness")
    checked = record.get("checkedAcceptance", [])
    ids = [row.get("acceptanceId") for row in checked]
    if len(ids) != len(set(ids)) or not set(case_ids).issubset(ids):
        raise ValueError("Review does not cover all distinct release acceptance cases")
    evidence = {}
    for row in checked:
        if row.get("acceptanceId") not in case_ids:
            continue
        if row.get("result") != "passed" or not row.get("note") or not row.get("evidencePaths"):
            raise ValueError("Review acceptance mapping needs passed results, substantive notes, and evidence paths")
        for relative in row["evidencePaths"]:
            p = safe_child(repo, relative, must_exist=True)
            if not p.is_file():
                raise ValueError(f"Review evidence is not a file: {relative}")
            evidence[relative] = file_digest(p)
    return {"path": str(path.relative_to(repo)), "sha256": file_digest(path), "independent": independent, "reviewer": identity, "evidence": [{"path": k, "sha256": v} for k, v in sorted(evidence.items())]}

def validate_plan(repo, plan, profile, requested):
    if plan.get("schemaVersion") != "1.0.0":
        raise ValueError("Unsupported verification plan schemaVersion")
    if plan.get("targetProfile") != profile:
        raise ValueError("Plan targetProfile must equal the requested profile")
    gate_catalog = read_json(PACK_ROOT / "contracts/gates.json")["gates"]
    required = {g["id"]: g for g in gate_catalog if profile in g["requiredProfiles"]}
    if not required:
        raise ValueError("Profile has no required gates")
    selected = set(requested) if requested else set(required)
    if not selected.issubset(required):
        raise ValueError("Requested gate is not part of this profile")
    all_cases = {c["id"] for c in read_json(PACK_ROOT / "contracts/acceptance-cases.json")["cases"]}
    rows = plan.get("gates", [])
    if not isinstance(rows, list) or len({r.get("id") for r in rows}) != len(rows):
        raise ValueError("Plan gates must have distinct IDs")
    lookup = {r["id"]: r for r in rows}
    if set(lookup) - {g["id"] for g in gate_catalog}:
        raise ValueError("Plan contains unknown gate IDs")
    if selected - set(lookup):
        raise ValueError("Plan is missing required gates: " + ", ".join(sorted(selected - set(lookup))))
    result = []
    command_ids = set()
    for gid in sorted(selected):
        commands = lookup[gid].get("commands", [])
        if not commands:
            raise ValueError(f"{gid} has no implemented verification commands; an example plan cannot qualify a product")
        covered = set()
        for command in commands:
            cid = command.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", cid) or cid in command_ids:
                raise ValueError("Command IDs must be unique, portable identifiers")
            command_ids.add(cid)
            argv = command.get("argv")
            if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a or "\0" in a for a in argv):
                raise ValueError(f"{cid} needs a nonempty argv array, not a shell command")
            cwd = safe_child(repo, command.get("cwd", "."), must_exist=True)
            if not cwd.is_dir():
                raise ValueError(f"{cid} cwd must be a directory")
            timeout = command.get("timeoutSeconds")
            if type(timeout) is not int or not 1 <= timeout <= 7200:
                raise ValueError(f"{cid} needs timeoutSeconds between 1 and 7200")
            if command.get("expectedExitCodes") != [0]:
                raise ValueError("A verification command must return zero after checking its own expected failures")
            cases = command.get("coversAcceptanceIds", [])
            if not cases or len(cases) != len(set(cases)) or not set(cases).issubset(all_cases):
                raise ValueError(f"{cid} has missing, repeated, or unknown acceptance IDs")
            if not set(cases).issubset(set(required[gid]["caseIds"])):
                raise ValueError(f"{cid} claims cases outside its gate")
            artifacts = command.get("evidenceArtifacts", [])
            if not isinstance(artifacts, list):
                raise ValueError("evidenceArtifacts must be a list")
            for item in artifacts:
                safe_child(repo, item)
            covered.update(cases)
        missing = set(required[gid]["caseIds"]) - covered
        if missing:
            raise ValueError(f"{gid} lacks acceptance mappings: {', '.join(sorted(missing))}")
        result.append({"id": gid, "commands": commands, "caseIds": required[gid]["caseIds"]})
    return result

def execute(repo, directory, gate, command, context):
    start = time.monotonic()
    log_relative = Path("evidence") / directory.name / (gate + "-" + command["id"] + ".log")
    log_path = state_path(repo, log_relative)
    timed_out = False
    error = None
    prior = {}
    for relative in command.get("evidenceArtifacts", []):
        p = safe_child(repo, relative)
        prior[relative] = (file_digest(p), p.stat().st_mtime_ns) if p.is_file() else None
    environment = dict(os.environ)
    environment.update(PRISM_GATE_RUN_ID=directory.name, PRISM_GATE_COMMAND_ID=command["id"], PRISM_GATE_SOURCE_SHA256=context["sourceFingerprintSha256"], PRISM_GATE_PLAN_SHA256=context["planSha256"], PRISM_GATE_EVIDENCE_DIR=str(directory))
    with tempfile.TemporaryFile(mode="w+b") as output:
        try:
            proc = subprocess.Popen(command["argv"], cwd=safe_child(repo, command.get("cwd", "."), must_exist=True), env=environment, stdout=output, stderr=subprocess.STDOUT, start_new_session=os.name == "posix")
            try:
                code = proc.wait(timeout=command["timeoutSeconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                code = proc.wait(timeout=10)
        except OSError as exc:
            code = None
            error = str(exc)
        output.seek(0, 2)
        size = output.tell()
        output.seek(0)
        log_path = state_path(repo, log_relative)
        with log_path.open("w", encoding="utf-8") as saved_log:
            os.chmod(log_path, 0o600)
            for line in output:
                saved_log.write(redact(line.decode(errors="replace")))
            if error:
                saved_log.write("\n" + redact(error))
    artifacts = []
    missing = []
    stale = []
    for index, relative in enumerate(command.get("evidenceArtifacts", [])):
        try:
            p = safe_child(repo, relative, must_exist=True)
            if not p.is_file():
                raise ValueError("Not a file")
            current_observation = (file_digest(p), p.stat().st_mtime_ns)
            if prior[relative] is not None and current_observation == prior[relative]:
                stale.append(relative)
            captured_dir = state_path(repo, Path("evidence") / directory.name / "artifacts")
            captured_dir.mkdir(mode=0o700, exist_ok=True)
            suffix = p.suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,12}", p.suffix) else ".bin"
            captured = state_path(repo, Path("evidence") / directory.name / "artifacts" / (gate + "-" + command["id"] + "-" + str(index) + suffix))
            shutil.copyfile(p, captured)
            os.chmod(captured, 0o600)
            artifacts.append({"path": str(captured.relative_to(repo)), "sourcePath": relative, "sha256": file_digest(captured), "bytes": captured.stat().st_size})
        except (ValueError, OSError):
            missing.append(relative)
    passed = code == 0 and not timed_out and not missing and not stale and error is None
    return {"id": command["id"], "gate": gate, "status": "passed" if passed else "failed", "argv": [redact(a) for a in command["argv"]], "cwd": command.get("cwd", "."), "exitCode": code, "timedOut": timed_out, "durationSeconds": round(time.monotonic() - start, 3), "log": str(log_path.relative_to(repo)), "logSha256": file_digest(log_path), "outputTruncated": False, "rawOutputBytes": size, "coversAcceptanceIds": command["coversAcceptanceIds"], "artifacts": artifacts, "missingArtifacts": missing, "staleArtifacts": stale, "error": redact(error) if error else None}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--profile", choices=["core", "web", "release"], default="core")
    parser.add_argument("--gate", action="append", default=[])
    parser.add_argument("--fingerprint", action="store_true")
    args = parser.parse_args()
    repo = repo_root(args.repo)
    state_path(repo)
    before = candidate_snapshot(repo)
    if args.fingerprint:
        result = {"status": "FINGERPRINTED", "sourceFingerprintSha256": before["sha256"], "commit": before["commit"], "clean": before["clean"], "dirtyPaths": before["dirtyPaths"], "files": len(before["entries"])}
        if args.plan:
            result["reviewedPlanSha256"] = file_digest(Path(args.plan).expanduser().resolve(strict=True))
        emit(result)
        return
    if not args.plan:
        raise ValueError("--plan is required unless --fingerprint is used")
    plan_path = Path(args.plan).expanduser().resolve(strict=True)
    plan = read_json(plan_path)
    plan_sha = digest(plan_path.read_bytes())
    gates = validate_plan(repo, plan, args.profile, args.gate)
    if (args.profile == "release" or plan.get("source", {}).get("requireCleanTree", True)) and not before["clean"]:
        raise ValueError("Verification requires a clean committed candidate; preserve and commit the intended changes first")
    review = None
    if args.profile == "release":
        case_ids = {case for g in read_json(PACK_ROOT / "contracts/gates.json")["gates"] if "release" in g["requiredProfiles"] for case in g["caseIds"]}
        review = check_review(repo, plan, plan_sha, before["sha256"], case_ids)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:10]
    directory = state_path(repo, Path("evidence") / run_id)
    directory.mkdir(parents=True, mode=0o700)
    atomic_write(directory / "plan.json", plan_path.read_bytes())
    receipt = {"schemaVersion": "1.0.0", "kind": "implementation-gate-run", "runId": run_id, "startedAt": stamp(), "profile": args.profile, "selectedGatesOnly": bool(args.gate), "sourceFingerprintSha256": before["sha256"], "sourceCommit": before["commit"], "sourceClean": before["clean"], "planSha256": plan_sha, "planPath": str(plan_path), "planSnapshot": str((directory / "plan.json").relative_to(repo)), "review": review, "environment": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine()}, "commands": [], "humanValidation": "DEFERRED", "status": "running"}
    write_json(directory / "source-fingerprint.json", before)
    receipt.update(sourceSnapshot=str((directory / "source-fingerprint.json").relative_to(repo)), sourceSnapshotSha256=file_digest(directory / "source-fingerprint.json"))
    write_json(directory / "receipt.json", receipt)
    for gate in gates:
        for command in gate["commands"]:
            observed = execute(repo, directory, gate["id"], command, receipt)
            receipt["commands"].append(observed)
            write_json(state_path(repo, Path("evidence") / run_id / "receipt.json"), receipt)
            emit({"gate": gate["id"], "command": command["id"], "status": observed["status"], "log": observed["log"]})
    after = candidate_snapshot(repo)
    unchanged = before["sha256"] == after["sha256"] and digest(plan_path.read_bytes()) == plan_sha
    if review:
        unchanged = unchanged and digest((repo / review["path"]).read_bytes()) == review["sha256"]
    evidence_errors = receipt_evidence_errors(repo, receipt)
    passed = unchanged and not evidence_errors and all(c["status"] == "passed" for c in receipt["commands"])
    status = "FAILED"
    if passed:
        status = "PASSED_SELECTED_GATES" if args.gate else "PASS"
        if review and not review["independent"]:
            status += "_WITH_DECLARED_REVIEW_FALLBACK"
    receipt.update(status=status, finishedAt=stamp(), sourceUnchanged=unchanged, evidenceErrors=evidence_errors, finalSourceFingerprintSha256=after["sha256"], acceptanceIds=sorted({a for c in receipt["commands"] if c["status"] == "passed" for a in c["coversAcceptanceIds"]}), claim="Observed command results and mapped acceptance evidence; semantic completeness depends on the reviewed test mapping. Human participant testing remains deferred.")
    write_json(state_path(repo, Path("evidence") / run_id / "receipt.json"), receipt)
    write_json(state_path(repo, "latest-" + args.profile + ".json"), {"receiptPath": str((directory / "receipt.json").relative_to(repo)), "receiptSha256": file_digest(directory / "receipt.json"), "status": status, "sourceFingerprintSha256": before["sha256"]})
    emit({"status": status, "profile": args.profile, "selectedGatesOnly": bool(args.gate), "sourceUnchanged": unchanged, "receipt": str(directory / "receipt.json"), "humanValidation": "DEFERRED"})
    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        emit({"status": "BLOCKED", "error": redact(str(exc)), "claim": "No implementation qualification was established"})
        sys.exit(2)

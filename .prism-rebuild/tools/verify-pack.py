#!/usr/bin/env python3
"""Verify the handoff's integrity and consistency, not product completion."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote
from prism_pack import PACK_ROOT, emit, pack_files, read_json, safe_child, verify_manifest

def ids(rows, label):
    values = [r["id"] for r in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label} IDs")
    return set(values)

def validate_contracts(root, schema_checks):
    requirements = read_json(root / "contracts/requirements.json")["requirements"]
    cases = read_json(root / "contracts/acceptance-cases.json")["cases"]
    milestones = read_json(root / "contracts/milestones.json")["milestones"]
    gates = read_json(root / "contracts/gates.json")["gates"]
    rid, cid, mid, gid = [ids(rows, name) for rows, name in [(requirements, "requirement"), (cases, "acceptance"), (milestones, "milestone"), (gates, "gate")]]
    case_map = {c["id"]: c for c in cases}
    requirement_map = {r["id"]: r for r in requirements}
    for req in requirements:
        if not re.fullmatch(r"REQ-[A-Z][A-Z0-9]*-\d{3}", req["id"]):
            raise ValueError("Malformed requirement ID")
        if req["milestone"] not in mid or not req.get("source"):
            raise ValueError(f"Missing milestone or provenance: {req['id']}")
        if not req["acceptanceIds"] or not set(req["acceptanceIds"]).issubset(cid):
            raise ValueError(f"Unmapped acceptance: {req['id']}")
        for case in req["acceptanceIds"]:
            if req["id"] not in case_map[case]["requirementIds"]:
                raise ValueError(f"Acceptance reverse link missing: {req['id']}/{case}")
    for case in cases:
        if not re.fullmatch(r"AC-[A-Z][A-Z0-9]*-\d{3}", case["id"]):
            raise ValueError("Malformed acceptance ID")
        if not case["requirementIds"] or not set(case["requirementIds"]).issubset(rid):
            raise ValueError(f"Unknown requirement: {case['id']}")
        for req in case["requirementIds"]:
            if case["id"] not in requirement_map[req]["acceptanceIds"]:
                raise ValueError(f"Requirement reverse link missing: {case['id']}/{req}")
        if not all(case.get(field) for field in ["given", "when", "then", "evidence", "gates"]):
            raise ValueError(f"Incomplete acceptance scenario: {case['id']}")
        if not set(case["gates"]).issubset(gid):
            raise ValueError(f"Unknown gate: {case['id']}")
    seen_requirements = set()
    deps = {}
    for milestone in milestones:
        if not set(milestone["requirementIds"]).issubset(rid) or not set(milestone["dependencyIds"]).issubset(mid):
            raise ValueError("Invalid milestone reference")
        for req in milestone["requirementIds"]:
            if requirement_map[req]["milestone"] != milestone["id"]:
                raise ValueError("Requirement belongs to a different milestone")
        seen_requirements.update(milestone["requirementIds"])
        deps[milestone["id"]] = milestone["dependencyIds"]
    if seen_requirements != rid:
        raise ValueError("Milestones do not cover all requirements")
    visiting, visited = set(), set()
    def walk(node):
        if node in visiting:
            raise ValueError("Milestone dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dep in deps[node]: walk(dep)
        visiting.remove(node)
        visited.add(node)
    for node in deps: walk(node)
    seen_cases = set()
    for gate in gates:
        if gate["milestone"] not in mid or not gate["caseIds"] or not set(gate["caseIds"]).issubset(cid):
            raise ValueError("Incomplete gate mapping")
        if not set(gate["requiredProfiles"]).issubset({"core", "web", "release"}):
            raise ValueError("Unknown verification profile")
        for case in gate["caseIds"]:
            if gate["id"] not in case_map[case]["gates"]:
                raise ValueError("Gate reverse link missing")
        seen_cases.update(gate["caseIds"])
    if seen_cases != cid:
        raise ValueError("Gates do not cover all acceptance cases")
    rule_data = read_json(root / "knowledge/rules.json")
    rules = rule_data["rules"]
    ids(rules, "knowledge rule")
    if rule_data["ruleCount"] != len(rules):
        raise ValueError("Knowledge ruleCount differs from actual rules")
    source_text = (root / "knowledge/SOURCES.md").read_text(encoding="utf-8")
    known_sources = set(re.findall(r"\b(?:B\d{2}|F\d{2}|U\d{2}|C\d{2}|P\d{2}|PROJECT)\b", source_text))
    for rule in rules:
        if not all(rule.get(k) for k in ["principle", "appliesWhen", "action", "check", "sourceIds", "authority"]):
            raise ValueError(f"Incomplete knowledge rule: {rule['id']}")
        if not set(rule["sourceIds"]).issubset(known_sources):
            raise ValueError(f"Unknown knowledge source: {rule['id']}")
    fixture_count = 0
    schema = read_json(root / "contracts/domain.schema.json")
    definitions = schema["$defs"]
    def walk_refs(value):
        if isinstance(value, list):
            for item in value: walk_refs(item)
        elif isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                if not reference.startswith("#/"):
                    raise ValueError(f"Domain schema reference must be local: {reference}")
                current = schema
                for part in reference[2:].split("/"):
                    part = part.replace("~1", "/").replace("~0", "~")
                    if not isinstance(current, dict) or part not in current:
                        raise ValueError(f"Missing schema reference: {reference}")
                    current = current[part]
            for item in value.values(): walk_refs(item)
    walk_refs(schema)
    catalogue = read_json(root / "contracts/command-catalog.json")
    operations = catalogue["operations"]
    operation_names = [o["name"] for o in operations]
    if len(operation_names) != len(set(operation_names)) or set(operation_names) != set(definitions["CommandName"]["enum"]):
        raise ValueError("Command catalogue and schema command names differ or repeat")
    for field in ["commonEnvelopeDefinition", "commonReceiptDefinition", "commonErrorDefinition"]:
        if catalogue[field] not in definitions:
            raise ValueError(f"Missing common command definition: {field}")
    error_codes = definitions["DomainError"]["properties"]["code"]["enum"]
    event_types = set(definitions["DomainEvent"]["properties"]["eventType"]["enum"])
    catalog_errors = [e["code"] for e in catalogue["errors"]]
    if len(catalog_errors) != len(set(catalog_errors)) or set(catalog_errors) != set(error_codes):
        raise ValueError("Command catalogue error codes differ from the schema")
    bindings = {}
    for branch in definitions["CommandEnvelope"]["allOf"]:
        name = branch.get("if", {}).get("properties", {}).get("command", {}).get("const")
        if name:
            if name in bindings: raise ValueError(f"Duplicate command payload binding: {name}")
            bindings[name] = branch["then"]["properties"]
    if set(bindings) != set(operation_names):
        raise ValueError("Command envelope does not bind every named operation")
    for operation in operations:
        name = operation["name"]
        for field, reference_field in [("inputDefinition", "inputSchema"), ("outputDefinition", "successSchema")]:
            definition = operation[field]
            if definition not in definitions or operation[reference_field].get("$ref") != "domain.schema.json#/$defs/" + definition:
                raise ValueError(f"Invalid {field} reference for {name}")
        if bindings[name]["payload"].get("$ref") != "#/$defs/" + operation["inputDefinition"]:
            raise ValueError(f"Command payload binding differs for {name}")
        if operation["kind"] not in {"query", "command"}:
            raise ValueError(f"Unknown operation kind: {name}")
        if operation["kind"] == "command" and (operation["idempotency"].get("required") is not True or bindings[name].get("idempotencyKey", {}).get("type") != "string"):
            raise ValueError(f"Mutation lacks required idempotency binding: {name}")
        if not set(operation["errors"]).issubset(error_codes) or not set(operation["events"]).issubset(event_types):
            raise ValueError(f"Unknown operation error/event: {name}")
        if not operation["requirementIds"] or not set(operation["requirementIds"]).issubset(rid):
            raise ValueError(f"Unknown or absent operation requirement mapping: {name}")
    if schema_checks:
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError as exc:
            raise ValueError("Full validation needs jsonschema. Install requirements-tools.txt in a local virtual environment, or use --integrity-only for a hash-only bootstrap check.") from exc
        Draft202012Validator.check_schema(schema)
        fixtures = read_json(root / "contracts/examples/manifest.json")["fixtures"]
        for fixture in fixtures:
            definition = fixture["definition"]
            if definition not in schema["$defs"]:
                raise ValueError(f"Fixture references unknown definition: {definition}")
            selected = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/" + definition}
            data = read_json(safe_child(root, fixture["path"], must_exist=True))
            valid = not list(Draft202012Validator(selected, format_checker=FormatChecker()).iter_errors(data))
            if valid is not fixture["valid"]:
                raise ValueError(f"Fixture outcome differs from specification: {fixture['path']}")
            fixture_count += 1
    return {"requirements": len(requirements), "acceptanceCases": len(cases), "milestones": len(milestones), "gates": len(gates), "knowledgeRules": len(rules), "schemaFixtures": fixture_count, "schemaDefinitions": len(definitions), "canonicalOperations": len(operations)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(PACK_ROOT))
    p.add_argument("--integrity-only", action="store_true")
    args = p.parse_args()
    root = Path(args.root).expanduser().resolve(strict=True)
    result = verify_manifest(root)
    if args.integrity_only:
        emit({"status": "PASS", "scope": "Handoff file integrity only; schemas, behavior and implementation NOT verified", **result})
        return
    files = pack_files(root)
    for path in files:
        if path.suffix == ".json":
            read_json(path)
        if path.suffix.lower() == ".pdf" or "project_sources" in path.relative_to(root).parts:
            raise ValueError("Source books are not part of this original handoff")
    broken = []
    for path in files:
        if path.suffix != ".md" and not path.name.endswith(".md.in"):
            continue
        text = path.read_text(encoding="utf-8")
        for raw in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text):
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) or raw.startswith("#"):
                continue
            target = unquote(raw.split("#", 1)[0])
            if not target:
                continue
            dest = (path.parent / target).resolve()
            if not dest.is_relative_to(root) or not dest.exists():
                broken.append(f"{path.relative_to(root)} -> {raw}")
    if broken:
        raise ValueError("Broken local Markdown links: " + "; ".join(broken))
    skill_paths = sorted((root / "blueprints/omp/skills").glob("*/SKILL.md.in"))
    if len(skill_paths) != 10:
        raise ValueError("Expected ten inactive external OMP skill blueprints")
    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        if not match:
            raise ValueError(f"Missing skill frontmatter: {path}")
        front = match.group(1)
        name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", front, re.M)
        if not name or name.group(1) != path.parent.name or not re.search(r"^description:\s*\S", front, re.M):
            raise ValueError(f"Invalid skill metadata: {path}")
        if len(text.split()) > 900:
            raise ValueError(f"Skill blueprint exceeds 900-word context ceiling: {path}")
    result.update(validate_contracts(root, True))
    emit({"status": "PASS", "scope": "Handoff integrity, links, traceability, skill-template structure and JSON Schema fixtures; NOT rebuilt application qualification", "skillBlueprints": len(skill_paths), **result})

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"status": "FAIL", "scope": "Handoff validation", "error": str(exc)})
        sys.exit(1)

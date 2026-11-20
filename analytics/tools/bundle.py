"""Integrity checks for immutable local report packages (trusted local publisher)."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

import duckdb

QUERIES = ("merchant_overview", "snapshot_share", "first_fixed_price", "promotion_mix",
           "vote_velocity", "comment_velocity", "deal_observation_audit")
MARTS = ("fct_deal_observation", "mart_deal_first_observed", "mart_merchant_snapshot", "mart_collection_quality")
FILES = {"analytics.duckdb", "contract.json", "acceptance.json", "README.md",
         "bin/report_query.py", "bin/comment_velocity.py", "bin/bundle.py"} | {f"sql/{n}.sql" for n in QUERIES}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text())


def valid_id(name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}", name):
        raise ValueError("Invalid release ID")
    return name


@dataclass(frozen=True)
class Package:
    root: Path
    manifest: dict
    contract: dict

    def connect(self):
        con = duckdb.connect(str(self.root / "analytics.duckdb"), read_only=True,
                             config={"enable_external_access": False})
        try:
            row = con.execute("""select comment from duckdb_tables()
                where database_name=current_database() and schema_name='analytics_marts'
                and table_name='mart_collection_quality'""").fetchone()
            if not row or row[0] != self.manifest["files"]["contract.json"]:
                raise ValueError("Database / report contract mismatch")
            return con
        except Exception:
            con.close()
            raise


def verify(root, manifest_hash=None):
    root = Path(root).resolve(strict=True)
    manifest_path = root / "manifest.json"
    expected_paths = FILES | {"manifest.json", "bin", "sql"}
    actual = {str(p.relative_to(root)) for p in root.rglob("*")}
    if actual != expected_paths or any((root / name).is_symlink() for name in actual):
        raise ValueError("Unexpected package file or symlink")
    if manifest_hash is not None and digest(manifest_path) != manifest_hash:
        raise ValueError("Manifest fingerprint mismatch")
    m = load_json(manifest_path)
    if valid_id(m["release_id"]) != root.name or set(m["files"]) != FILES:
        raise ValueError("Invalid package ID or inventory")
    for name, sha in m["files"].items():
        p = root / name
        if p.resolve() != p or not p.is_file() or digest(p) != sha:
            raise ValueError(f"Package hash mismatch: {name}")
    contract = load_json(root / "contract.json")
    acceptance = load_json(root / "acceptance.json")
    if (contract["release_id"] != m["release_id"] or contract["version"] != m["metric_contract_version"]
        or set(contract["queries"]) != set(QUERIES) or acceptance["status"] != "passed"
        or acceptance["release_id"] != m["release_id"]):
        raise ValueError("Contract or acceptance mismatch")
    for name in QUERIES:
        if contract["queries"][name]["sql_sha256"] != m["files"][f"sql/{name}.sql"]:
            raise ValueError(f"Query / contract mismatch: {name}")
    if duckdb.__version__ != m["dependencies"]["duckdb"]:
        raise ValueError(f"This package requires duckdb {m['dependencies']['duckdb']}")
    pkg = Package(root, m, contract)
    with pkg.connect() as con:
        if con.execute("select current_database()").fetchone()[0] != "analytics":
            raise ValueError("Wrong catalog")
    return pkg


def resolve(store=None, version=None):
    # Read current exactly once; all further file reads use this immutable version directory.
    here = Path(__file__).resolve().parent.parent
    if store is None and version is None and (here / "manifest.json").is_file():
        return verify(here)
    store = Path(store).resolve() if store is not None else here / "local"
    if version is None:
        selection = load_json(store / "current")
        version = valid_id(selection["release_id"])
    else:
        version = valid_id(version)
        selection = load_json(store / "qualified" / (version + ".json"))
    return verify(store / "versions" / version, selection["manifest_sha256"])

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)
LEGACY_SKILLS = ("chinese-law-paper-writing", *SKILLS[1:])
BUNDLE_ID = "hermes-legal-research-skills"
LOCK_NAME = "bundle-lock.json"
IGNORED_NAMES = {"__pycache__", ".DS_Store"}
SCHEMA_VERSION = 1
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ARCHIVE_SUFFIX = "/archive/refs/heads/main.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_skill_files(skill_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(skill_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(
                f"symlinked release content is not supported: "
                f"{path.relative_to(skill_dir).as_posix()}"
            )
        if (
            not path.is_file()
            or LOCK_NAME in path.parts
            or any(part in IGNORED_NAMES for part in path.parts)
            or path.suffix == ".pyc"
        ):
            continue
        files[path.relative_to(skill_dir).as_posix()] = sha256_file(path)
    return files


def _collect_skill_files_for_manifest(skill_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(skill_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(
                f"symlinked release content is not supported: "
                f"{path.relative_to(skill_dir).as_posix()}"
            )
        if not path.is_file() or any(part in IGNORED_NAMES for part in path.parts):
            continue
        if path.suffix == ".pyc":
            continue
        files[path.relative_to(skill_dir).as_posix()] = sha256_file(path)
    return files


def read_skill_version(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(
        r"^\s{2}version:\s*[\"']?(\d+\.\d+\.\d+)[\"']?\s*$",
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing metadata.version: {skill_dir}")
    return match.group(1)


def build_lock(
    skill_name: str,
    skill_version: str,
    bundle_version: str,
    files: dict[str, str],
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "bundle_version": bundle_version,
        "skill_name": skill_name,
        "skill_version": skill_version,
        "files": dict(files),
    }


def _validate_semver(value: str, field: str) -> None:
    if not isinstance(value, str) or not SEMVER_RE.fullmatch(value):
        raise ValueError(f"invalid {field}: {value!r}")
    first, second, _ = value.split(".")
    if len(first) == 4:
        major = int(first)
        try:
            if 2000 <= major <= 2099 and len(second) == 4:
                date(major, int(second[:2]), int(second[2:]))
            else:
                date(2000 + major // 100, major % 100, int(second))
        except ValueError as exc:
            raise ValueError(f"invalid calendar {field}: {value!r}") from exc


def _validate_archive_url(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.endswith(ARCHIVE_SUFFIX)
        or len(parsed.path.strip("/").split("/")) < 5
    ):
        raise ValueError(f"invalid archive_url: {value!r}")


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _normalize_release_input(root: Path, release: dict, *, skill_names: tuple[str, ...] = SKILLS) -> dict:
    required = {"bundle_version", "published_at", "update_level", "summary", "changes", "archive_url"}
    missing = required - set(release)
    if missing:
        raise ValueError(f"missing release fields: {sorted(missing)}")

    bundle_version = str(release["bundle_version"])
    _validate_semver(bundle_version, "bundle_version")

    published_at = str(release["published_at"])
    try:
        datetime.fromisoformat(published_at)
    except ValueError as exc:
        raise ValueError(f"invalid published_at: {published_at!r}") from exc

    archive_url = str(release["archive_url"])
    _validate_archive_url(archive_url)

    changes = release["changes"]
    if not isinstance(changes, list) or not all(isinstance(item, str) for item in changes):
        raise ValueError("changes must be a list[str]")

    summary = str(release["summary"])
    update_level = str(release["update_level"])

    skills: dict[str, str] = {}
    files: dict[str, str] = {}
    other_writing_name = LEGACY_SKILLS[0] if skill_names == SKILLS else SKILLS[0]
    other_writing_path = root / other_writing_name
    if other_writing_path.exists() or other_writing_path.is_symlink():
        raise ValueError(f"release contains an unsupported writing skill alias: {other_writing_name}")
    for skill_name in skill_names:
        skill_dir = root / skill_name
        if skill_dir.is_symlink():
            raise ValueError(f"symlinked release Skill directory is not supported: {skill_name}")
        if not skill_dir.is_dir():
            raise ValueError(f"missing skill directory: {skill_name}")
        skill_md = skill_dir / "SKILL.md"
        openai_yaml = skill_dir / "agents" / "openai.yaml"
        if not skill_md.is_file():
            raise ValueError(f"missing SKILL.md: {skill_name}")
        if not openai_yaml.is_file():
            raise ValueError(f"missing agents/openai.yaml: {skill_name}")
        skill_version = read_skill_version(skill_dir)
        _validate_semver(skill_version, f"{skill_name}.version")
        if re.fullmatch(r"\d{4}\.\d{1,2}\.\d+", bundle_version) and skill_version != bundle_version:
            raise ValueError(f"date release skill version must equal bundle_version: {skill_name}")
        skills[skill_name] = skill_version
        for relative_path, digest in _collect_skill_files_for_manifest(skill_dir).items():
            files[f"{skill_name}/{relative_path}"] = digest

    release_skills = release.get("skills")
    if release_skills is not None:
        if not isinstance(release_skills, dict):
            raise ValueError("skills must be a mapping")
        if {str(key) for key in release_skills} != set(skill_names):
            raise ValueError("skills must match the managed skill set")
        for skill_name, skill_version in skills.items():
            if str(release_skills[skill_name]) != skill_version:
                raise ValueError(f"skill version mismatch: {skill_name}")

    compatibility = release.get("compatibility")
    if compatibility is None:
        compatibility = {"hermes": True, "codex": True, "python": ">=3.9"}
    elif not isinstance(compatibility, dict):
        raise ValueError("compatibility must be a mapping")

    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "bundle_version": bundle_version,
        "published_at": published_at,
        "update_level": update_level,
        "summary": summary,
        "skills": skills,
        "compatibility": compatibility,
        "changes": list(changes),
        "archive_url": archive_url,
        "files": files,
    }


def build_manifest(root: Path, release: dict, *, legacy_baseline: bool = False) -> dict:
    skill_names = LEGACY_SKILLS if legacy_baseline else SKILLS
    manifest = _normalize_release_input(root, release, skill_names=skill_names)

    current_entry = {
        "bundle_version": manifest["bundle_version"],
        "published_at": manifest["published_at"],
        "update_level": manifest["update_level"],
        "summary": manifest["summary"],
        "changes": list(manifest["changes"]),
    }

    existing = _load_json(root / "bundle-release.json")
    history: list[dict] = []
    if existing and isinstance(existing.get("history"), list):
        for entry in existing["history"]:
            if isinstance(entry, dict) and entry.get("bundle_version") != current_entry["bundle_version"]:
                history.append(dict(entry))
    history.append(current_entry)

    manifest["history"] = history
    return manifest


def _release_from_existing_manifest(existing: dict) -> dict:
    release = {}
    for key in ("bundle_version", "published_at", "update_level", "summary", "changes", "archive_url", "compatibility", "skills"):
        if key in existing:
            release[key] = existing[key]
    return release


def _write_json(path: Path, data: dict) -> None:
    # open(..., newline=) instead of Path.write_text(newline=): the latter
    # needs Python 3.10, and the bundle supports Python 3.9+.
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _write_locks(root: Path, release: dict) -> None:
    bundle_version = str(release["bundle_version"])
    for skill_name in SKILLS:
        skill_dir = root / skill_name
        skill_version = read_skill_version(skill_dir)
        lock = build_lock(skill_name, skill_version, bundle_version, collect_skill_files(skill_dir))
        _write_json(skill_dir / LOCK_NAME, lock)


def _check_locks(root: Path, bundle_version: str, *, skill_names: tuple[str, ...] = SKILLS) -> bool:
    for skill_name in skill_names:
        skill_dir = root / skill_name
        expected = build_lock(
            skill_name,
            read_skill_version(skill_dir),
            bundle_version,
            collect_skill_files(skill_dir),
        )
        lock_path = skill_dir / LOCK_NAME
        try:
            existing = _load_json(lock_path)
        except ValueError as exc:
            print(f"{skill_name}/{LOCK_NAME} is invalid: {exc}", file=sys.stderr)
            return False
        if existing != expected:
            print(f"{skill_name}/{LOCK_NAME} differs from expected content", file=sys.stderr)
            return False
    return True


def _resolve_release(root: Path, args: argparse.Namespace) -> dict:
    existing = _load_json(root / "bundle-release.json")
    if existing:
        release = _release_from_existing_manifest(existing)
    else:
        release = {}
    if isinstance(release.get("compatibility"), dict):
        release["compatibility"] = dict(release["compatibility"])
        release["compatibility"].pop("claude_code", None)
    if args.bundle_version is not None:
        release["bundle_version"] = args.bundle_version
        # A new release derives its skill identities/versions from the tree;
        # the previous manifest remains the history/check baseline only.
        release.pop("skills", None)
    if args.published_at is not None:
        release["published_at"] = args.published_at
    if args.update_level is not None:
        release["update_level"] = args.update_level
    if args.summary is not None:
        release["summary"] = args.summary
    if args.change:
        release["changes"] = list(args.change)
    if existing is None and args.bundle_version is None:
        raise ValueError("missing release metadata for first write")
    if "changes" not in release:
        raise ValueError("missing release changes")
    if "bundle_version" not in release:
        raise ValueError("missing bundle_version")
    if "published_at" not in release:
        raise ValueError("missing published_at")
    if "update_level" not in release:
        raise ValueError("missing update_level")
    if "summary" not in release:
        raise ValueError("missing summary")
    if "archive_url" not in release:
        release["archive_url"] = (
            "https://github.com/shawndeng321/"
            "legal-academic-research-skills/"
            "archive/refs/heads/main.zip"
        )
    return release


def _command_write(root: Path, args: argparse.Namespace) -> int:
    release = _resolve_release(root, args)
    # Validate the whole input before writing even the first lock. The
    # manifest is rebuilt after locks are written to include their hashes.
    _normalize_release_input(root, release)
    _write_locks(root, release)
    manifest = build_manifest(root, release)
    _write_json(root / "bundle-release.json", manifest)
    return 0


def _command_check(root: Path) -> int:
    manifest_path = root / "bundle-release.json"
    existing = _load_json(manifest_path)
    if existing is None:
        print("bundle-release.json is missing", file=sys.stderr)
        return 1
    existing_skills = existing.get("skills")
    if not isinstance(existing_skills, dict) or set(existing_skills) not in (set(SKILLS), set(LEGACY_SKILLS)):
        print("manifest skills must match a supported schema-1 skill set", file=sys.stderr)
        return 1
    legacy_baseline = set(existing_skills) == set(LEGACY_SKILLS)
    skill_names = LEGACY_SKILLS if legacy_baseline else SKILLS
    release = _release_from_existing_manifest(existing)
    if "archive_url" in existing:
        release["archive_url"] = existing["archive_url"]
    if not _check_locks(root, str(existing.get("bundle_version", "")), skill_names=skill_names):
        return 1
    expected = build_manifest(root, release, legacy_baseline=legacy_baseline)
    if expected != existing:
        print("bundle-release.json differs from expected content", file=sys.stderr)
        return 1
    print(f"Bundle {expected['bundle_version']} is consistent")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare legal skills bundle release metadata.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bundle-version")
    parser.add_argument("--published-at")
    parser.add_argument("--update-level")
    parser.add_argument("--summary")
    parser.add_argument("--change", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.write == args.check:
        raise SystemExit("choose exactly one of --write or --check")
    root = ROOT
    if args.write:
        return _command_write(root, args)
    return _command_check(root)


if __name__ == "__main__":
    raise SystemExit(main())

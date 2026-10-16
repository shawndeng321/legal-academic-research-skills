from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "tools" / "prepare_bundle_release.py"
UPDATER = ROOT / "legal-research-wiki" / "scripts" / "legal_skills_update.py"
SKILLS = (
    "law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)


class CanonicalTemporaryDirectory(tempfile.TemporaryDirectory):
    """TemporaryDirectory yielding a symlink-free (canonical) path.

    The updater rejects any path whose ancestors contain a symlink, by
    design. Fixtures hand temporary roots straight to the updater, so the
    path must be canonical: on macOS the default TMPDIR sits under /var,
    which is itself a symlink to /private/var, and a raw
    TemporaryDirectory path would be rejected for that reason alone.
    """

    def __enter__(self) -> str:
        return str(Path(super().__enter__()).resolve())


def make_manifest(version: str, history: list[dict] | None = None) -> dict:
    return {
        "schema_version": 1,
        "bundle_id": "hermes-legal-research-skills",
        "bundle_version": version,
        "published_at": "2026-08-10T00:00:00+08:00",
        "update_level": "feature",
        "summary": f"Bundle {version}",
        "skills": {
            "law-paper-writing": "5.1.0",
            "legal-research-wiki": "4.1.0",
            "legal-wiki-audit-repair": "4.2.0",
        },
        "compatibility": {"hermes": True, "codex": True, "python": ">=3.11"},
        "changes": [f"Change {version}"],
        "archive_url": (
            "https://github.com/shawndeng321/"
            "legal-academic-research-skills/"
            "archive/refs/heads/main.zip"
        ),
        "files": {
            "law-paper-writing/SKILL.md": "a" * 64,
            "law-paper-writing/agents/openai.yaml": "b" * 64,
            "legal-research-wiki/SKILL.md": "c" * 64,
            "legal-research-wiki/agents/openai.yaml": "d" * 64,
            "legal-wiki-audit-repair/SKILL.md": "e" * 64,
            "legal-wiki-audit-repair/agents/openai.yaml": "f" * 64,
        },
        "history": history if history is not None else [
            {
                "bundle_version": version,
                "published_at": "2026-08-10T00:00:00+08:00",
                "update_level": "feature",
                "summary": f"Bundle {version}",
                "changes": [f"Change {version}"],
            }
        ],
    }


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def make_bundle_fixture(version: str = "1.1.0") -> tuple[dict, dict[str, bytes]]:
    files = {
        "law-paper-writing/SKILL.md": b"paper skill\n",
        "law-paper-writing/agents/openai.yaml": b"paper agent\n",
        "legal-research-wiki/SKILL.md": b"wiki skill\n",
        "legal-research-wiki/agents/openai.yaml": b"wiki agent\n",
        "legal-wiki-audit-repair/SKILL.md": b"audit skill\n",
        "legal-wiki-audit-repair/agents/openai.yaml": b"audit agent\n",
    }
    manifest = make_manifest(version)
    manifest["files"] = {
        path: sha256_bytes(content) for path, content in files.items()
    }
    return manifest, files


def write_zip(
    archive: Path,
    members: dict[str, bytes],
    *,
    symlinks: set[str] | None = None,
) -> Path:
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in members.items():
            if symlinks and name in symlinks:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(info, content)
            elif "\\" in name:
                info = zipfile.ZipInfo(name.replace("\\", "/"))
                info.filename = name
                info.orig_filename = name
                bundle.writestr(info, content)
            else:
                bundle.writestr(name, content)
    archive.write_bytes(memory.getvalue())
    return archive


def bundle_members(
    manifest: dict,
    files: dict[str, bytes],
    *,
    prefix: str = "repository-root/",
) -> dict[str, bytes]:
    release = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {
        f"{prefix}bundle-release.json": release,
        **{f"{prefix}{path}": content for path, content in files.items()},
    }


def write_installed_skill(
    skills_root: Path,
    skill_name: str,
    files: dict[str, bytes],
    *,
    bundle_version: str = "1.0.0",
) -> None:
    skill_root = skills_root / skill_name
    for relative_path, content in files.items():
        path = skill_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    lock = {
        "schema_version": 1,
        "bundle_id": "hermes-legal-research-skills",
        "bundle_version": bundle_version,
        "skill_name": skill_name,
        "skill_version": "1.0.0",
        "files": {
            path: sha256_bytes(content) for path, content in files.items()
        },
    }
    (skill_root / "bundle-lock.json").write_text(
        json.dumps(lock, sort_keys=True), encoding="utf-8"
    )


def write_installation(skills_root: Path) -> dict[str, dict[str, bytes]]:
    installed = {
        "law-paper-writing": {
            "SKILL.md": b"local paper\n",
            "agents/openai.yaml": b"local paper agent\n",
        },
        "legal-research-wiki": {
            "SKILL.md": b"local wiki\n",
            "agents/openai.yaml": b"local wiki agent\n",
        },
        "legal-wiki-audit-repair": {
            "SKILL.md": b"local audit\n",
            "agents/openai.yaml": b"local audit agent\n",
        },
    }
    for skill_name, files in installed.items():
        write_installed_skill(skills_root, skill_name, files)
    return installed


def write_staged_bundle(
    bundle_root: Path,
    manifest: dict,
    files: dict[str, bytes],
) -> None:
    bundle_root.mkdir(parents=True, exist_ok=True)
    (bundle_root / "bundle-release.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    for relative_path, content in files.items():
        path = bundle_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def make_transaction_bundle(version: str = "1.1.0") -> tuple[dict, dict[str, bytes]]:
    manifest = make_manifest(version)
    files: dict[str, bytes] = {}
    for skill_name in SKILLS:
        skill_files = {
            "SKILL.md": f"incoming {skill_name}\n".encode(),
            "agents/openai.yaml": f"incoming agent {skill_name}\n".encode(),
        }
        lock = {
            "schema_version": 1,
            "bundle_id": "hermes-legal-research-skills",
            "bundle_version": version,
            "skill_name": skill_name,
            "skill_version": manifest["skills"][skill_name],
            "files": {
                relative: sha256_bytes(content)
                for relative, content in skill_files.items()
            },
        }
        skill_files["bundle-lock.json"] = (
            json.dumps(lock, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode("utf-8")
        for relative, content in skill_files.items():
            files[f"{skill_name}/{relative}"] = content
    manifest["files"] = {
        relative: sha256_bytes(content) for relative, content in files.items()
    }
    return manifest, files


def snapshot_tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def read_bundle_versions(skills_root: Path) -> set[str]:
    return {
        json.loads((skills_root / name / "bundle-lock.json").read_text(encoding="utf-8"))[
            "bundle_version"
        ]
        for name in SKILLS
    }


@contextmanager
def updater_fixture(
    state: dict | None = None,
    last_check: float | None = None,
):
    with CanonicalTemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / "law-paper-writing"
        skill_dir.mkdir()
        (skill_dir / "bundle-lock.json").write_text(
            json.dumps({"bundle_version": "1.0.0"}), encoding="utf-8"
        )
        state_base = root / "state-base"
        state_root = state_base / "hermes-legal-research-skills"
        state_root.mkdir(parents=True)
        initial = dict(state or {})
        if last_check is not None:
            initial["last_network_check"] = last_check
        if initial:
            (state_root / "state.json").write_text(
                json.dumps(initial), encoding="utf-8"
            )
        # Isolate the state root on ALL platforms, not just Windows:
        #   - Windows: LOCALAPPDATA
        #   - macOS/Linux: XDG_STATE_HOME, falling back to HOME/.local/state
        # Without HOME isolation, macOS/Linux tests would read/write the real
        # ~/.local/state/hermes-legal-research-skills/ and pollute each other.
        isolated_home = root / "isolated-home"
        isolated_home.mkdir()
        with patch.dict(
            os.environ,
            {
                "LOCALAPPDATA": str(state_base),
                "XDG_STATE_HOME": str(state_base),
                "HOME": str(isolated_home),
            },
            clear=False,
        ):
            yield SimpleNamespace(
                root=root,
                skill_dir=skill_dir,
                state_root=state_root,
                state_path=state_root / "state.json",
            )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_skill(root: Path, name: str, version: str) -> Path:
    skill = root / name
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        f'name: "{name}"\n'
        'description: "Use when updating a legal skill bundle."\n'
        'license: "MIT"\n'
        "metadata:\n"
        f'  version: "{version}"\n'
        "---\n\n"
        "# Demo\n",
        encoding="utf-8",
    )
    (skill / "agents" / "openai.yaml").write_text(
        "interface:\n"
        f'  display_name: "{name}"\n'
        '  short_description: "demo skill"\n'
        f'  default_prompt: "Use ${name} to update."\n',
        encoding="utf-8",
    )
    return skill


def prepare_temporary_repository(root: Path) -> None:
    tool = root / "tools" / "prepare_bundle_release.py"
    tool.parent.mkdir(parents=True)
    shutil.copy2(PREPARE, tool)
    for skill_name, version in zip(SKILLS, ("5.1.0", "4.1.0", "4.2.0")):
        write_skill(root, skill_name, version)


def run_prepare(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    tool = root / "tools" / "prepare_bundle_release.py"
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(tool), *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def write_release(root: Path) -> subprocess.CompletedProcess[str]:
    return run_prepare(
        root,
        "--write",
        "--bundle-version",
        "1.0.0",
        "--published-at",
        "2026-08-10T00:00:00+08:00",
        "--update-level",
        "feature",
        "--summary",
        "增加按需更新检查、统一备份和回滚",
        "--change",
        "增加每6小时一次的按需更新检查",
    )


class ReleaseContractTests(unittest.TestCase):
    def test_repository_manifest_and_updater_copies_use_supported_contracts(self):
        # Release locks are generated by the final packaging step, not by
        # updater development. Read either schema-1 naming generation here;
        # CLI lock/hash consistency is exercised in isolated release fixtures.
        manifest = json.loads((ROOT / "bundle-release.json").read_text(encoding="utf-8"))
        module = load_module(UPDATER, "repository_manifest_contract")
        self.assertEqual(module.validate_manifest(manifest), manifest)
        updater_bytes = {
            (ROOT / skill_name / "scripts" / "legal_skills_update.py").read_bytes()
            for skill_name in manifest["skills"]
        }
        self.assertEqual(len(updater_bytes), 1)

    def test_cli_write_and_check_succeeds(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_temporary_repository(root)

            written = write_release(root)

            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertTrue((root / "bundle-release.json").is_file())
            for skill_name in SKILLS:
                self.assertTrue((root / skill_name / "bundle-lock.json").is_file())

            checked = run_prepare(root, "--check")

            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("Bundle 1.0.0 is consistent", checked.stdout)

    def test_cli_check_rejects_tampered_lock_even_when_manifest_hash_matches(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_temporary_repository(root)
            written = write_release(root)
            self.assertEqual(written.returncode, 0, written.stderr)

            skill_name = SKILLS[0]
            lock_path = root / skill_name / "bundle-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["bundle_version"] = "9.9.9"
            lock_path.write_text(
                json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            manifest_path = root / "bundle-release.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][f"{skill_name}/bundle-lock.json"] = hashlib.sha256(
                lock_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            checked = run_prepare(root, "--check")

            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("bundle-lock.json", checked.stderr)

    def test_collect_skill_files_is_stable_and_excludes_lock_and_cache(self):
        module = load_module(PREPARE, "prepare_bundle_release_collect")
        with CanonicalTemporaryDirectory() as tmp:
            skill = Path(tmp) / "demo"
            (skill / "scripts" / "__pycache__").mkdir(parents=True)
            (skill / "SKILL.md").write_text("demo", encoding="utf-8")
            (skill / "bundle-lock.json").write_text("{}", encoding="utf-8")
            (skill / "scripts" / "tool.py").write_text("print(1)\n", encoding="utf-8")
            (skill / "scripts" / "__pycache__" / "tool.pyc").write_bytes(b"cache")

            files = module.collect_skill_files(skill)

            self.assertEqual(set(files), {"SKILL.md", "scripts/tool.py"})
            self.assertRegex(files["SKILL.md"], r"^[0-9a-f]{64}$")

    def test_collect_skill_files_rejects_symlinked_release_content(self):
        module = load_module(PREPARE, "prepare_bundle_release_symlink")
        with CanonicalTemporaryDirectory() as tmp:
            skill = Path(tmp) / "demo"
            skill.mkdir()
            linked_path = skill / "linked.txt"
            linked_path.write_text("simulated link target\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(path):
                if path == linked_path:
                    return True
                return original_is_symlink(path)

            with patch.object(Path, "is_symlink", simulated_is_symlink):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    module.collect_skill_files(skill)

    def test_read_skill_version_reads_metadata_version(self):
        module = load_module(PREPARE, "prepare_bundle_release_version")
        with CanonicalTemporaryDirectory() as tmp:
            skill = write_skill(Path(tmp), "demo-skill", "2.3.4")

            version = module.read_skill_version(skill)

            self.assertEqual(version, "2.3.4")

    def test_build_lock_uses_exact_contract(self):
        module = load_module(PREPARE, "prepare_bundle_lock")
        lock = module.build_lock("demo-skill", "2.3.4", "1.0.0", {"SKILL.md": "a" * 64})
        self.assertEqual(lock, {
            "schema_version": 1,
            "bundle_id": "hermes-legal-research-skills",
            "bundle_version": "1.0.0",
            "skill_name": "demo-skill",
            "skill_version": "2.3.4",
            "files": {"SKILL.md": "a" * 64},
        })

    def test_build_manifest_replaces_existing_history_entry(self):
        module = load_module(PREPARE, "prepare_bundle_manifest")
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            for skill_name, version in zip(SKILLS, ("5.1.0", "4.1.0", "4.2.0")):
                write_skill(root, skill_name, version)

            first_release = {
                "bundle_version": "1.0.0",
                "published_at": "2026-08-10T00:00:00+08:00",
                "update_level": "feature",
                "summary": "旧说明",
                "changes": ["旧说明"],
                "archive_url": (
                    "https://github.com/shawndeng321/"
                    "legal-academic-research-skills/"
                    "archive/refs/heads/main.zip"
                ),
            }
            first_manifest = module.build_manifest(root, first_release)
            (root / "bundle-release.json").write_text(
                json.dumps(first_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            second_release = {
                "bundle_version": "1.0.0",
                "published_at": "2026-08-10T00:00:00+08:00",
                "update_level": "feature",
                "summary": "增加按需更新检查、统一备份和回滚",
                "changes": [
                    "增加每6小时一次的按需更新检查",
                    "增加三个Skill统一备份、校验、更新和失败回滚",
                    "增加本地修改检测、稍后提醒和忽略当前版本",
                ],
                "archive_url": (
                    "https://github.com/shawndeng321/"
                    "legal-academic-research-skills/"
                    "archive/refs/heads/main.zip"
                ),
            }

            manifest = module.build_manifest(root, second_release)

            self.assertEqual(len(manifest["history"]), 1)
            self.assertEqual(manifest["history"][0]["bundle_version"], "1.0.0")
            self.assertEqual(
                manifest["history"][0]["changes"],
                [
                    "增加每6小时一次的按需更新检查",
                    "增加三个Skill统一备份、校验、更新和失败回滚",
                    "增加本地修改检测、稍后提醒和忽略当前版本",
                ],
            )

    def test_build_manifest_rejects_missing_metadata_and_invalid_archive_url(self):
        module = load_module(PREPARE, "prepare_bundle_validation")
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "law-paper-writing", "5.1.0")
            write_skill(root, "legal-research-wiki", "4.1.0")
            broken = write_skill(root, "legal-wiki-audit-repair", "4.2.0")
            (broken / "SKILL.md").unlink()

            release = {
                "bundle_version": "1.0.0",
                "published_at": "2026-08-10T00:00:00+08:00",
                "update_level": "feature",
                "summary": "增加按需更新检查、统一备份和回滚",
                "changes": ["增加每6小时一次的按需更新检查"],
                "archive_url": (
                    "https://github.com/shawndeng321/"
                    "legal-academic-research-skills/"
                    "archive/refs/heads/main.zip"
                ),
            }

            with self.assertRaises(ValueError):
                module.build_manifest(root, release)

        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            for skill_name, version in zip(SKILLS, ("5.1.0", "4.1.0", "4.2.0")):
                write_skill(root, skill_name, version)

            release = {
                "bundle_version": "1.0.0",
                "published_at": "2026-08-10T00:00:00+08:00",
                "update_level": "feature",
                "summary": "增加按需更新检查、统一备份和回滚",
                "changes": ["增加每6小时一次的按需更新检查"],
                "archive_url": "http://example.com/archive.zip",
            }

            with self.assertRaises(ValueError):
                module.build_manifest(root, release)


class ArchiveSafetyTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"legal_skills_archive_{self._testMethodName}")
        self.manifest, self.files = make_bundle_fixture()

    def test_extracts_a_valid_bundle_only_after_validation(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = write_zip(
                root / "bundle.zip", bundle_members(self.manifest, self.files)
            )

            bundle_root = self.module.safe_extract_bundle(
                archive, root / "staging", self.manifest
            )

            self.assertEqual(bundle_root, root / "staging" / "repository-root")
            self.assertEqual(
                (bundle_root / "law-paper-writing" / "SKILL.md").read_bytes(),
                b"paper skill\n",
            )
            self.module.verify_staged_bundle(bundle_root, self.manifest)

    def test_accepts_full_repository_archive_but_extracts_only_managed_bundle(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            members = bundle_members(self.manifest, self.files)
            members.update(
                {
                    "repository-root/README.md": b"repository readme\n",
                    "repository-root/docs/design.md": b"design\n",
                    "repository-root/tests/test_release.py": b"def test_release(): pass\n",
                    "repository-root/tools/prepare_bundle_release.py": b"print('tool')\n",
                }
            )
            archive = write_zip(root / "main.zip", members)

            bundle_root = self.module.safe_extract_bundle(
                archive, root / "staging", self.manifest
            )

            self.module.verify_staged_bundle(bundle_root, self.manifest)
            self.assertFalse((bundle_root / "README.md").exists())
            self.assertFalse((bundle_root / "docs").exists())
            self.assertFalse((bundle_root / "tests").exists())
            self.assertFalse((bundle_root / "tools").exists())

    def test_rejects_traversal_absolute_drive_and_backslash_paths_before_writing(self):
        hostile_members = (
            "../escape.txt",
            "/absolute.txt",
            "repository-root/../../escape.txt",
            "C:/drive.txt",
            "repository-root\\ambiguous.txt",
        )
        for index, member in enumerate(hostile_members):
            with self.subTest(member=member), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                members = bundle_members(self.manifest, self.files)
                members[member] = b"bad"
                archive = write_zip(root / f"hostile-{index}.zip", members)
                destination = root / "staging"
                destination.mkdir()

                with self.assertRaises(self.module.ArchiveError):
                    self.module.safe_extract_bundle(
                        archive, destination, self.manifest
                    )

                self.assertEqual(list(destination.iterdir()), [])
                self.assertFalse((root / "escape.txt").exists())

    def test_rejects_symlink_entries_before_writing(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            members = bundle_members(self.manifest, self.files)
            link_name = "repository-root/law-paper-writing/link"
            members[link_name] = b"../../escape.txt"
            archive = write_zip(root / "symlink.zip", members, symlinks={link_name})
            destination = root / "staging"
            destination.mkdir()

            with self.assertRaisesRegex(self.module.ArchiveError, "symlink"):
                self.module.safe_extract_bundle(archive, destination, self.manifest)

            self.assertEqual(list(destination.iterdir()), [])

    def test_rejects_case_fold_collisions_before_writing(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            members = bundle_members(self.manifest, self.files)
            members["repository-root/Law-Paper-Writing/SKILL.md"] = b"collision"
            archive = write_zip(root / "collision.zip", members)
            destination = root / "staging"
            destination.mkdir()

            with self.assertRaisesRegex(self.module.ArchiveError, "case-fold"):
                self.module.safe_extract_bundle(archive, destination, self.manifest)

            self.assertEqual(list(destination.iterdir()), [])

    def test_rejects_archive_compressed_uncompressed_and_file_count_limits(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = write_zip(
                root / "bundle.zip", bundle_members(self.manifest, self.files)
            )
            for limit_name in (
                "MAX_ARCHIVE_BYTES",
                "MAX_UNCOMPRESSED_BYTES",
                "MAX_ARCHIVE_FILES",
            ):
                with self.subTest(limit=limit_name):
                    destination = root / limit_name
                    destination.mkdir()
                    with patch.object(self.module, limit_name, 1):
                        with self.assertRaises(self.module.ArchiveError):
                            self.module.safe_extract_bundle(
                                archive, destination, self.manifest
                            )
                    self.assertEqual(list(destination.iterdir()), [])

    def test_rejects_missing_extra_and_hash_mismatched_files_before_writing(self):
        cases: list[tuple[str, dict[str, bytes]]] = []
        missing = bundle_members(self.manifest, self.files)
        missing.pop("repository-root/legal-research-wiki/SKILL.md")
        cases.append(("missing", missing))
        extra = bundle_members(self.manifest, self.files)
        extra["repository-root/legal-research-wiki/unlisted.txt"] = b"extra"
        cases.append(("extra", extra))
        mismatched = bundle_members(self.manifest, self.files)
        mismatched["repository-root/legal-wiki-audit-repair/SKILL.md"] = b"tampered"
        cases.append(("hash", mismatched))

        for index, (case_name, members) in enumerate(cases):
            with self.subTest(case=case_name), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = write_zip(root / f"case-{index}.zip", members)
                destination = root / "staging"
                destination.mkdir()

                with self.assertRaises(self.module.ArchiveError):
                    self.module.safe_extract_bundle(
                        archive, destination, self.manifest
                    )

                self.assertEqual(list(destination.iterdir()), [])

    def test_rejects_archive_manifest_drift_before_writing(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            drifted = json.loads(json.dumps(self.manifest))
            drifted["skills"]["legal-research-wiki"] = "9.9.9"
            members = bundle_members(drifted, self.files)
            archive = write_zip(root / "drifted.zip", members)
            destination = root / "staging"
            destination.mkdir()

            with self.assertRaisesRegex(self.module.ArchiveError, "manifest"):
                self.module.safe_extract_bundle(archive, destination, self.manifest)

            self.assertEqual(list(destination.iterdir()), [])

    def test_rejects_unsafe_paths_in_the_checked_manifest_before_writing(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            unsafe_manifest = json.loads(json.dumps(self.manifest))
            unsafe_manifest["files"]["../outside.txt"] = sha256_bytes(b"bad")
            members = bundle_members(unsafe_manifest, {**self.files, "../outside.txt": b"bad"})
            archive = write_zip(root / "unsafe-manifest.zip", members)
            destination = root / "staging"
            destination.mkdir()

            with self.assertRaises(self.module.ArchiveError):
                self.module.safe_extract_bundle(
                    archive, destination, unsafe_manifest
                )

            self.assertEqual(list(destination.iterdir()), [])
            self.assertFalse((root / "outside.txt").exists())

    def test_verify_staged_bundle_rejects_missing_skill_extra_file_wrong_hash_and_drift(self):
        mutations = ("missing_skill", "extra", "hash", "drift")
        for mutation in mutations:
            with self.subTest(mutation=mutation), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = json.loads(json.dumps(self.manifest))
                files = dict(self.files)
                write_staged_bundle(root, manifest, files)
                if mutation == "missing_skill":
                    shutil.rmtree(root / "legal-research-wiki")
                elif mutation == "extra":
                    (root / "extra.txt").write_text("extra", encoding="utf-8")
                elif mutation == "hash":
                    (root / "law-paper-writing" / "SKILL.md").write_text(
                        "tampered", encoding="utf-8"
                    )
                else:
                    release_path = root / "bundle-release.json"
                    release = json.loads(release_path.read_text(encoding="utf-8"))
                    release["bundle_version"] = "9.9.9"
                    release_path.write_text(json.dumps(release), encoding="utf-8")

                with self.assertRaises(self.module.ArchiveError):
                    self.module.verify_staged_bundle(root, self.manifest)


class InstallationInspectionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"legal_skills_install_{self._testMethodName}")
        self.manifest, _ = make_bundle_fixture()

    def test_clean_installation_has_exact_report_shape_and_is_not_modified(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            write_installation(root)
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }

            report = self.module.inspect_installation(root, self.manifest)

            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(report, {
                "status": "clean",
                "modified": [],
                "deleted": [],
                "added": [],
                "missing_skills": [],
            })
            self.assertEqual(after, before)

    def test_classifies_modified_deleted_and_added_files_against_local_locks(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            write_installation(root)
            (root / "law-paper-writing" / "SKILL.md").write_text(
                "locally modified\n", encoding="utf-8"
            )
            (root / "legal-research-wiki" / "agents" / "openai.yaml").unlink()
            added = root / "legal-wiki-audit-repair" / "notes" / "local.txt"
            added.parent.mkdir()
            added.write_text("local extra\n", encoding="utf-8")

            report = self.module.inspect_installation(root, self.manifest)

            self.assertEqual(report, {
                "status": "local_changes",
                "modified": ["law-paper-writing/SKILL.md"],
                "deleted": ["legal-research-wiki/agents/openai.yaml"],
                "added": ["legal-wiki-audit-repair/notes/local.txt"],
                "missing_skills": [],
            })

    def test_classifies_a_missing_skill_without_writing(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            write_installation(root)
            shutil.rmtree(root / "legal-research-wiki")
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            report = self.module.inspect_installation(root, self.manifest)

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(report, {
                "status": "local_changes",
                "modified": [],
                "deleted": [],
                "added": [],
                "missing_skills": ["legal-research-wiki"],
            })
            self.assertEqual(after, before)

    def test_classifies_invalid_local_lock_metadata_as_modified(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            write_installation(root)
            lock_path = root / "law-paper-writing" / "bundle-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["bundle_version"] = "not-semver"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")

            report = self.module.inspect_installation(root, self.manifest)

            self.assertEqual(report, {
                "status": "local_changes",
                "modified": ["law-paper-writing/bundle-lock.json"],
                "deleted": [],
                "added": [],
                "missing_skills": [],
            })

    def test_formats_small_utf8_changes_as_unified_diff(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = root / "installed"
            staged = root / "staged"
            relative = Path("law-paper-writing/SKILL.md")
            (installed / relative).parent.mkdir(parents=True)
            (staged / relative).parent.mkdir(parents=True)
            (installed / relative).write_text("old line\n", encoding="utf-8")
            (staged / relative).write_text("new line\n", encoding="utf-8")

            result = self.module.format_incoming_diff(
                installed, staged, [relative.as_posix()]
            )

            self.assertIn("--- installed/law-paper-writing/SKILL.md", result)
            self.assertIn("+++ incoming/law-paper-writing/SKILL.md", result)
            self.assertIn("-old line", result)
            self.assertIn("+new line", result)

    def test_formats_binary_and_large_changes_as_hash_only(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = root / "installed"
            staged = root / "staged"
            binary_path = Path("law-paper-writing/assets/data.bin")
            large_path = Path("legal-research-wiki/references/large.txt")
            old_binary, new_binary = b"\xff\x00old", b"\xff\x00new"
            old_large = b"a" * (1024 * 1024)
            new_large = b"b" * (1024 * 1024)
            for base, relative, content in (
                (installed, binary_path, old_binary),
                (staged, binary_path, new_binary),
                (installed, large_path, old_large),
                (staged, large_path, new_large),
            ):
                (base / relative).parent.mkdir(parents=True, exist_ok=True)
                (base / relative).write_bytes(content)

            result = self.module.format_incoming_diff(
                installed,
                staged,
                [binary_path.as_posix(), large_path.as_posix()],
            )

            for relative, old_content, new_content in (
                (binary_path, old_binary, new_binary),
                (large_path, old_large, new_large),
            ):
                self.assertIn(relative.as_posix(), result)
                self.assertIn(sha256_bytes(old_content), result)
                self.assertIn(sha256_bytes(new_content), result)
            self.assertNotIn("a" * 100, result)
            self.assertNotIn("b" * 100, result)


class SourceTransactionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"legal_skills_transaction_{self._testMethodName}")

    @contextmanager
    def fixture(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            staged_root = root / "staged"
            state_root = root / "state"
            skills_root.mkdir()
            state_root.mkdir()
            manifest, files = make_transaction_bundle()
            write_installation(skills_root)
            write_staged_bundle(staged_root, manifest, files)
            yield SimpleNamespace(
                root=root,
                skills_root=skills_root,
                staged_root=staged_root,
                state_root=state_root,
                manifest=manifest,
            )

    def test_detects_a_normal_source_copy_installation(self):
        with self.fixture() as fixture:
            self.assertEqual(
                self.module.detect_installation_mode(fixture.skills_root, SKILLS),
                "source-copy",
            )

    def test_recognizes_claude_code_plugin_directories(self):
        module = self.module
        self.assertTrue(module.is_claude_plugin_path(
            Path("/home/u/.claude/plugins/cache/m/p/2.0.0/law-paper-writing"), env={}
        ))
        self.assertTrue(module.is_claude_plugin_path(
            Path("/opt/cfg/plugins/cache/m/p/2.0.0"), env={}
        ))
        self.assertTrue(module.is_claude_plugin_path(
            Path("/opt/custom/plugins/marketplaces/m"), env={"CLAUDE_CONFIG_DIR": "/opt/custom"}
        ))
        self.assertFalse(module.is_claude_plugin_path(
            Path("/home/u/.claude/skills/law-paper-writing"), env={}
        ))
        self.assertFalse(module.is_claude_plugin_path(
            Path("/home/u/.codex/skills"), env={}
        ))

    def test_refuses_to_apply_into_a_claude_code_plugin_directory(self):
        with CanonicalTemporaryDirectory() as tmp:
            skills_root = Path(tmp) / ".claude" / "plugins" / "cache" / "m" / "p" / "2.0.0"
            skills_root.mkdir(parents=True)
            write_installation(skills_root)
            with self.assertRaises(self.module.ArchiveError):
                self.module.detect_installation_mode(skills_root, SKILLS)

    def test_check_reports_update_channel(self):
        with CanonicalTemporaryDirectory() as tmp:
            plugin_skill = Path(tmp) / ".claude" / "plugins" / "cache" / "m" / "p" / "2.0.0" / SKILLS[0]
            plain_skill = Path(tmp) / "skills" / SKILLS[0]
            calls = []

            def fake_inner(skill_dir, **kwargs):
                calls.append(skill_dir)
                return {"status": "cached", "fatal": False}

            with patch.object(self.module, "_check_for_update", fake_inner):
                self.assertEqual(
                    self.module.check_for_update(plugin_skill)["update_channel"],
                    "claude-plugin",
                )
                self.assertEqual(
                    self.module.check_for_update(plain_skill)["update_channel"],
                    "bundle",
                )
            self.assertEqual(calls, [plugin_skill, plain_skill])

    def test_applies_three_skills_and_keeps_timestamped_backup(self):
        with self.fixture() as fixture:
            result = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
            )

            self.assertEqual(result["status"], "updated")
            self.assertEqual(read_bundle_versions(fixture.skills_root), {"1.1.0"})
            backup = Path(result["backup_path"])
            self.assertTrue(backup.is_dir())
            self.assertTrue((backup / "transaction.json").is_file())
            self.assertEqual(
                sorted(path.name for path in backup.iterdir() if path.is_dir()),
                sorted(SKILLS),
            )
            self.assertTrue((fixture.state_root / "worker" / "legal_skills_update.py").is_file())

    def _group_into_category(self, skills_root: Path) -> Path:
        """Mimic Hermes: one Skill at the top level, two under a category folder."""
        category = skills_root / "research"
        category.mkdir()
        for skill_name in SKILLS[1:]:
            (skills_root / skill_name).rename(category / skill_name)
        return category

    def test_updates_skills_grouped_in_category_folders_in_place(self):
        with self.fixture() as fixture:
            category = self._group_into_category(fixture.skills_root)
            self.assertEqual(
                self.module.detect_installation_mode(fixture.skills_root, SKILLS),
                "source-copy",
            )
            report = self.module.inspect_installation(fixture.skills_root, fixture.manifest)
            self.assertEqual(report["missing_skills"], [])

            result = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
            )

            self.assertEqual(result["status"], "updated", result)
            self.assertTrue((fixture.skills_root / SKILLS[0] / "bundle-lock.json").is_file())
            for skill_name in SKILLS[1:]:
                self.assertFalse((fixture.skills_root / skill_name).exists())
                lock = json.loads(
                    (category / skill_name / "bundle-lock.json").read_text(encoding="utf-8")
                )
                self.assertEqual(lock["bundle_version"], "1.1.0")
            transaction = json.loads(
                (Path(result["backup_path"]) / "transaction.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                Path(transaction["skill_paths"][SKILLS[1]]),
                (category / SKILLS[1]).resolve(),
            )

    def test_rejects_a_skill_installed_twice(self):
        with self.fixture() as fixture:
            category = self._group_into_category(fixture.skills_root)
            shutil.copytree(category / SKILLS[1], fixture.skills_root / SKILLS[1])
            with self.assertRaises(self.module.ArchiveError):
                self.module.detect_installation_mode(fixture.skills_root, SKILLS)

    def test_fault_restores_skills_to_their_category_folders(self):
        with self.fixture() as fixture:
            category = self._group_into_category(fixture.skills_root)
            before = {
                skill_name: (category / skill_name / "SKILL.md").read_bytes()
                for skill_name in SKILLS[1:]
            }

            def fail_after_second(skill_name):
                if skill_name == SKILLS[1]:
                    raise RuntimeError("simulated failure")

            result = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                fault_hook=fail_after_second,
            )

            self.assertEqual(result["status"], "rolled_back", result)
            for skill_name in SKILLS[1:]:
                self.assertEqual(
                    (category / skill_name / "SKILL.md").read_bytes(), before[skill_name]
                )
                self.assertFalse((fixture.skills_root / skill_name).exists())

    def test_fault_after_second_skill_restores_all_old_directories(self):
        with self.fixture() as fixture:
            before = snapshot_tree(fixture.skills_root)

            def fail_after_second(skill_name):
                if skill_name == SKILLS[1]:
                    raise RuntimeError("simulated second-skill failure")

            result = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                fault_hook=fail_after_second,
            )

            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(snapshot_tree(fixture.skills_root), before)


def make_hermes_lock(skills_root: Path, *, version: int = 1) -> dict:
    installed = {}
    repository = "shawndeng321/legal-academic-research-skills"
    for skill_name in SKILLS:
        skill_root = skills_root / skill_name
        content_hash = hashlib.sha256()
        for path in sorted(skill_root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(skill_root).as_posix()
                content_hash.update(relative.encode("utf-8"))
                content_hash.update(b"\0")
                content_hash.update(path.read_bytes())
        installed[skill_name] = {
            "source": "github",
            "identifier": f"{repository}/{skill_name}",
            "trust_level": "community",
            "scan_verdict": "safe",
            "content_hash": content_hash.hexdigest(),
            "install_path": skill_name,
            "files": ["SKILL.md", "agents/openai.yaml", "bundle-lock.json"],
        }
    installed["unrelated-skill"] = {
        "source": "github",
        "identifier": "someone/other-repository/unrelated-skill",
        "install_path": "unrelated-skill",
        "content_hash": "sha256:unrelated",
    }
    return {"version": version, "installed": installed}


def write_hermes_lock(path: Path, data: dict) -> bytes:
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


class HermesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"legal_skills_hermes_{self._testMethodName}")

    @contextmanager
    def fixture(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            state_root = root / "state"
            lock_path = skills_root / ".hub" / "lock.json"
            skills_root.mkdir()
            state_root.mkdir()
            manifest, files = make_transaction_bundle()
            write_installation(skills_root)
            lock = make_hermes_lock(skills_root)
            write_hermes_lock(lock_path, lock)
            yield SimpleNamespace(
                root=root,
                skills_root=skills_root,
                state_root=state_root,
                lock_path=lock_path,
                manifest=manifest,
                files=files,
                lock=lock,
            )

    def install_incoming(self, fixture, skill_name):
        skill_root = fixture.skills_root / skill_name
        for relative, content in fixture.files.items():
            prefix = f"{skill_name}/"
            if relative.startswith(prefix):
                path = skill_root / relative[len(prefix):]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

    def test_reads_and_detects_three_target_skills_from_one_github_repository(self):
        with self.fixture() as fixture:
            lock = self.module.read_hermes_lock(fixture.lock_path)
            detected = self.module.detect_hermes_bundle(lock, fixture.skills_root)

        self.assertEqual(detected["repository"], "shawndeng321/legal-academic-research-skills")
        self.assertEqual(detected["skills"], list(SKILLS))

    def test_rejects_mixed_sources_and_unknown_lock_versions(self):
        with self.fixture() as fixture:
            mixed = json.loads(json.dumps(fixture.lock))
            mixed["installed"][SKILLS[1]]["source"] = "official"
            with self.assertRaises(self.module.ArchiveError):
                self.module.detect_hermes_bundle(mixed, fixture.skills_root)

            with self.assertRaises(self.module.ArchiveError):
                self.module.detect_hermes_bundle(
                    {**fixture.lock, "version": 2}, fixture.skills_root
                )

    def test_updates_each_skill_with_an_explicit_command_and_keeps_unrelated_lock_entry(self):
        with self.fixture() as fixture:
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                self.install_incoming(fixture, command[-1])
                return subprocess.CompletedProcess(command, 0, "updated\n", "")

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            expected = [
                ["hermes", "skills", "update", "law-paper-writing"],
                ["hermes", "skills", "update", "legal-research-wiki"],
                ["hermes", "skills", "update", "legal-wiki-audit-repair"],
            ]
            self.assertEqual(commands, expected)
            self.assertEqual(result["status"], "updated")
            self.assertEqual(
                json.loads(fixture.lock_path.read_text(encoding="utf-8"))["installed"]["unrelated-skill"],
                fixture.lock["installed"]["unrelated-skill"],
            )

    def test_successful_commands_with_unrelated_lock_drift_require_manual_recovery(self):
        with self.fixture() as fixture:
            before_dirs = {
                skill_name: snapshot_tree(fixture.skills_root / skill_name)
                for skill_name in SKILLS
            }

            def runner(command, **kwargs):
                self.install_incoming(fixture, command[-1])
                if command[-1] == SKILLS[-1]:
                    current = json.loads(fixture.lock_path.read_text(encoding="utf-8"))
                    current["installed"]["unrelated-skill"]["updated_at"] = "concurrent"
                    write_hermes_lock(fixture.lock_path, current)
                return subprocess.CompletedProcess(command, 0, "", "")

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            self.assertEqual(result["status"], "manual_recovery_required")
            for skill_name in SKILLS:
                self.assertEqual(
                    snapshot_tree(fixture.skills_root / skill_name),
                    before_dirs[skill_name],
                )
            backup = Path(result["backup_path"])
            self.assertTrue((backup / "hermes-lock.before.json").is_file())
            self.assertTrue((backup / "hermes-lock.after.json").is_file())

    def test_post_update_lock_read_failure_rolls_back_target_directories(self):
        with self.fixture() as fixture:
            before_dirs = {
                skill_name: snapshot_tree(fixture.skills_root / skill_name)
                for skill_name in SKILLS
            }
            original_read_bytes = Path.read_bytes
            update_started = False

            def fail_post_update_lock_read(path):
                if path == fixture.lock_path and update_started:
                    raise OSError("simulated post-update lock read failure")
                return original_read_bytes(path)

            def runner(command, **kwargs):
                nonlocal update_started
                update_started = True
                self.install_incoming(fixture, command[-1])
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(Path, "read_bytes", fail_post_update_lock_read):
                result = self.module.apply_hermes_transaction(
                    fixture.skills_root,
                    fixture.lock_path,
                    fixture.manifest,
                    fixture.state_root,
                    runner=runner,
                )

            self.assertEqual(result["status"], "manual_recovery_required")
            for skill_name in SKILLS:
                self.assertEqual(
                    snapshot_tree(fixture.skills_root / skill_name),
                    before_dirs[skill_name],
                )

    def test_command_two_failure_restores_all_directories_and_exact_lock_bytes(self):
        with self.fixture() as fixture:
            before_dirs = snapshot_tree(fixture.skills_root)
            before_lock = fixture.lock_path.read_bytes()
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.install_incoming(fixture, command[-1])
                if len(calls) == 2:
                    return subprocess.CompletedProcess(command, 1, "", "failed")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(snapshot_tree(fixture.skills_root), before_dirs)
            self.assertEqual(fixture.lock_path.read_bytes(), before_lock)

    def test_hash_mismatch_rolls_back_directories_and_lock(self):
        with self.fixture() as fixture:
            before_dirs = snapshot_tree(fixture.skills_root)
            before_lock = fixture.lock_path.read_bytes()

            def runner(command, **kwargs):
                self.install_incoming(fixture, command[-1])
                if command[-1] == SKILLS[-1]:
                    (fixture.skills_root / command[-1] / "SKILL.md").write_bytes(b"tampered\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(snapshot_tree(fixture.skills_root), before_dirs)
            self.assertEqual(fixture.lock_path.read_bytes(), before_lock)

    def test_unrelated_lock_change_requires_manual_recovery_and_preserves_both_lock_copies(self):
        with self.fixture() as fixture:
            before_dirs = {
                skill_name: snapshot_tree(fixture.skills_root / skill_name)
                for skill_name in SKILLS
            }
            before_lock = fixture.lock_path.read_bytes()

            def runner(command, **kwargs):
                self.install_incoming(fixture, command[-1])
                if command[-1] == SKILLS[-1]:
                    current = json.loads(fixture.lock_path.read_text(encoding="utf-8"))
                    current["installed"]["unrelated-skill"]["updated_at"] = "concurrent"
                    write_hermes_lock(fixture.lock_path, current)
                return subprocess.CompletedProcess(
                    command,
                    1 if command[-1] == SKILLS[-1] else 0,
                    "",
                    "failed" if command[-1] == SKILLS[-1] else "",
                )

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            self.assertEqual(result["status"], "manual_recovery_required")
            self.assertEqual(
                {
                    skill_name: snapshot_tree(fixture.skills_root / skill_name)
                    for skill_name in SKILLS
                },
                before_dirs,
            )
            self.assertNotEqual(fixture.lock_path.read_bytes(), before_lock)
            backup = Path(result["backup_path"])
            self.assertEqual((backup / "hermes-lock.before.json").read_bytes(), before_lock)
            self.assertEqual((backup / "hermes-lock.after.json").read_bytes(), fixture.lock_path.read_bytes())

    def test_local_changes_require_confirmation_but_can_be_explicitly_allowed(self):
        with self.fixture() as fixture:
            (fixture.skills_root / SKILLS[0] / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.install_incoming(fixture, command[-1])
                return subprocess.CompletedProcess(command, 0, "", "")

            blocked = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )
            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertEqual(calls, [])

            allowed = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
                allow_local_changes=True,
            )
            self.assertEqual(allowed["status"], "updated")

    def test_missing_content_hash_treated_as_local_change(self):
        with self.fixture() as fixture:
            lock = json.loads(fixture.lock_path.read_text(encoding="utf-8"))
            del lock["installed"][SKILLS[0]]["content_hash"]
            write_hermes_lock(fixture.lock_path, lock)
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.install_incoming(fixture, command[-1])
                return subprocess.CompletedProcess(command, 0, "", "")

            blocked = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
            )

            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertEqual(calls, [])
            self.assertEqual(blocked["report"]["status"], "local_changes")

    def test_added_and_deleted_files_require_confirmation(self):
        cases = (
            ("added", lambda fixture: (fixture.skills_root / SKILLS[0] / "extra.txt").write_text("extra\n", encoding="utf-8")),
            ("deleted", lambda fixture: (fixture.skills_root / SKILLS[0] / "agents" / "openai.yaml").unlink()),
        )
        for case_name, mutate in cases:
            with self.subTest(case=case_name), self.fixture() as fixture:
                mutate(fixture)
                calls = []

                def runner(command, **kwargs):
                    calls.append(command)
                    self.install_incoming(fixture, command[-1])
                    return subprocess.CompletedProcess(command, 0, "", "")

                blocked = self.module.apply_hermes_transaction(
                    fixture.skills_root,
                    fixture.lock_path,
                    fixture.manifest,
                    fixture.state_root,
                    runner=runner,
                )

                self.assertEqual(blocked["status"], "confirmation_required")
                self.assertEqual(calls, [])
                self.assertEqual(blocked["report"]["status"], "local_changes")
                self.assertTrue(blocked["report"]["added"] or blocked["report"]["deleted"])

    def test_symlinked_local_content_requires_confirmation_without_link_privileges(self):
        with self.fixture() as fixture:
            linked_path = fixture.skills_root / SKILLS[0] / "SKILL.md"
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(path):
                if path == linked_path:
                    return True
                return original_is_symlink(path)

            with patch.object(Path, "is_symlink", simulated_is_symlink):
                blocked = self.module.apply_hermes_transaction(
                    fixture.skills_root,
                    fixture.lock_path,
                    fixture.manifest,
                    fixture.state_root,
                    runner=lambda *_args, **_kwargs: self.fail("runner must not be called"),
                )

            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertIn(
                f"{SKILLS[0]}/SKILL.md",
                blocked["report"]["symlinked"],
            )

    def test_symlink_report_alone_requires_confirmation(self):
        with self.fixture() as fixture:
            report = {
                "status": "local_changes",
                "modified": [],
                "deleted": [],
                "added": [],
                "symlinked": [f"{SKILLS[0]}/SKILL.md"],
                "missing_skills": [],
                "unknown_integrity": [],
            }
            with patch.object(
                self.module,
                "_hermes_local_report",
                return_value=report,
            ):
                blocked = self.module.apply_hermes_transaction(
                    fixture.skills_root,
                    fixture.lock_path,
                    fixture.manifest,
                    fixture.state_root,
                    runner=lambda *_args, **_kwargs: self.fail("runner must not be called"),
                )

            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertEqual(blocked["report"], report)

    def test_extra_file_during_update_rolls_back_directories_and_lock(self):
        with self.fixture() as fixture:
            before_dirs = snapshot_tree(fixture.skills_root)
            before_lock = fixture.lock_path.read_bytes()

            def runner(command, **kwargs):
                self.install_incoming(fixture, command[-1])
                if command[-1] == SKILLS[-1]:
                    (fixture.skills_root / command[-1] / "unexpected.txt").write_text(
                        "unexpected\n",
                        encoding="utf-8",
                    )
                return subprocess.CompletedProcess(command, 0, "", "")

            result = self.module.apply_hermes_transaction(
                fixture.skills_root,
                fixture.lock_path,
                fixture.manifest,
                fixture.state_root,
                runner=runner,
                allow_local_changes=True,
            )

            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(snapshot_tree(fixture.skills_root), before_dirs)
            self.assertEqual(fixture.lock_path.read_bytes(), before_lock)

    def test_symlinked_content_after_update_rolls_back_without_link_privileges(self):
        with self.fixture() as fixture:
            before_dirs = snapshot_tree(fixture.skills_root)
            before_lock = fixture.lock_path.read_bytes()
            linked_path = fixture.skills_root / SKILLS[-1] / "SKILL.md"
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(path):
                if path == linked_path:
                    return True
                return original_is_symlink(path)

            def runner(command, **kwargs):
                self.install_incoming(fixture, command[-1])
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(Path, "is_symlink", simulated_is_symlink):
                result = self.module.apply_hermes_transaction(
                    fixture.skills_root,
                    fixture.lock_path,
                    fixture.manifest,
                    fixture.state_root,
                    runner=runner,
                    allow_local_changes=True,
                )

            self.assertEqual(result["status"], "rolled_back")
            self.assertEqual(snapshot_tree(fixture.skills_root), before_dirs)
            self.assertEqual(fixture.lock_path.read_bytes(), before_lock)

class SourceTransactionContinuationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"legal_skills_transaction_continuation_{self._testMethodName}")

    @contextmanager
    def fixture(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            staged_root = root / "staged"
            state_root = root / "state"
            skills_root.mkdir()
            state_root.mkdir()
            manifest, files = make_transaction_bundle()
            write_installation(skills_root)
            write_staged_bundle(staged_root, manifest, files)
            yield SimpleNamespace(
                root=root,
                skills_root=skills_root,
                staged_root=staged_root,
                state_root=state_root,
                manifest=manifest,
            )

    def test_local_changes_need_an_independent_confirmation(self):
        with self.fixture() as fixture:
            local_file = fixture.skills_root / SKILLS[0] / "SKILL.md"
            local_file.write_text("local edit\n", encoding="utf-8")
            before = snapshot_tree(fixture.skills_root)

            blocked = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
            )
            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertEqual(snapshot_tree(fixture.skills_root), before)

            allowed = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                allow_local_changes=True,
            )
            self.assertEqual(allowed["status"], "updated")

    def test_missing_skill_needs_an_independent_install_confirmation(self):
        with self.fixture() as fixture:
            shutil.rmtree(fixture.skills_root / SKILLS[1])

            blocked = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                allow_local_changes=True,
            )
            self.assertEqual(blocked["status"], "confirmation_required")
            self.assertEqual(blocked["report"]["missing_skills"], [SKILLS[1]])
            self.assertFalse((fixture.skills_root / SKILLS[1]).exists())

            allowed = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                install_missing=True,
            )
            self.assertEqual(allowed["status"], "updated")

    def test_local_and_missing_flags_are_not_inferred_from_each_other(self):
        with self.fixture() as fixture:
            shutil.rmtree(fixture.skills_root / SKILLS[1])
            (fixture.skills_root / SKILLS[0] / "SKILL.md").write_text(
                "local edit\n", encoding="utf-8"
            )

            local_only = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                allow_local_changes=True,
            )
            self.assertEqual(local_only["status"], "confirmation_required")

            missing_only = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
                install_missing=True,
            )
            self.assertEqual(missing_only["status"], "confirmation_required")

    def test_rejects_git_worktrees_and_symlink_skill_directories(self):
        with self.fixture() as fixture:
            (fixture.skills_root / SKILLS[0] / ".git").write_text(
                "gitdir: ../.git/worktrees/paper\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(self.module.ArchiveError, "Git"):
                self.module.detect_installation_mode(fixture.skills_root, SKILLS)

        with self.fixture() as fixture:
            target = fixture.skills_root / SKILLS[0]
            with patch.object(
                self.module.Path,
                "is_symlink",
                autospec=True,
                side_effect=lambda path: path == target,
            ):
                with self.assertRaisesRegex(self.module.ArchiveError, "symlink"):
                    self.module.detect_installation_mode(fixture.skills_root, SKILLS)

    def test_rejects_overlapping_transaction_paths_before_any_state_write(self):
        cases = (
            (
                "state-inside-skills",
                lambda fixture: fixture.skills_root / "transaction-state",
                lambda fixture: fixture.root / "invalid-staged",
            ),
            (
                "state-inside-managed-skill",
                lambda fixture: fixture.skills_root / SKILLS[0] / "transaction-state",
                lambda fixture: fixture.root / "invalid-staged",
            ),
            (
                "state-inside-staged",
                lambda fixture: fixture.staged_root / "transaction-state",
                lambda fixture: fixture.staged_root,
            ),
            (
                "staged-inside-skills",
                lambda fixture: fixture.root / "unused-state",
                lambda fixture: fixture.skills_root / "invalid-staged",
            ),
            (
                "staged-is-managed-skill",
                lambda fixture: fixture.root / "unused-state",
                lambda fixture: fixture.skills_root / SKILLS[0],
            ),
        )
        for name, state_path, staged_path in cases:
            with self.subTest(name=name), self.fixture() as fixture:
                before = snapshot_tree(fixture.skills_root)
                state_root = state_path(fixture)
                staged_root = staged_path(fixture)

                result = self.module.apply_source_transaction(
                    fixture.skills_root,
                    staged_root,
                    fixture.manifest,
                    state_root,
                )

                self.assertEqual(result["status"], "rejected")
                self.assertEqual(snapshot_tree(fixture.skills_root), before)
                self.assertFalse(state_root.exists())
                self.assertFalse(
                    any(path.is_file() for path in fixture.root.rglob("state.json"))
                )

    def test_cli_diff_emits_a_bounded_json_success_result(self):
        with self.fixture() as fixture:
            manifest_path = fixture.root / "cached-manifest.json"
            manifest_path.write_text(
                json.dumps(fixture.manifest), encoding="utf-8"
            )
            unrelated = fixture.root / "unrelated-working-directory"
            unrelated.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(UPDATER),
                    "diff",
                    "--skills-root",
                    str(fixture.skills_root),
                    "--staged-root",
                    str(fixture.staged_root),
                    "--manifest",
                    str(manifest_path),
                    "--state-root",
                    str(fixture.state_root),
                    "--json",
                ],
                cwd=unrelated,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "clean")
            self.assertIn("incoming/", payload["diff"])

    def test_cli_apply_reexecutes_the_private_worker_for_a_successful_update(self):
        with self.fixture() as fixture:
            manifest_path = fixture.root / "cached-manifest.json"
            manifest_path.write_text(
                json.dumps(fixture.manifest), encoding="utf-8"
            )
            unrelated = fixture.root / "unrelated-working-directory"
            unrelated.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(UPDATER),
                    "apply",
                    "--skills-root",
                    str(fixture.skills_root),
                    "--staged-root",
                    str(fixture.staged_root),
                    "--manifest",
                    str(manifest_path),
                    "--state-root",
                    str(fixture.state_root),
                    "--allow-local-changes",
                    "--json",
                ],
                cwd=unrelated,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "updated")
            self.assertEqual(read_bundle_versions(fixture.skills_root), {"1.1.0"})
            self.assertTrue((fixture.state_root / "worker" / UPDATER.name).is_file())

    def test_two_simultaneous_applies_yield_one_updated_and_one_busy(self):
        with self.fixture() as fixture:
            entered = threading.Event()
            release = threading.Event()
            results = []

            def hold_after_first(skill_name):
                if skill_name == SKILLS[0]:
                    entered.set()
                    self.assertTrue(release.wait(5))

            first = threading.Thread(
                target=lambda: results.append(
                    self.module.apply_source_transaction(
                        fixture.skills_root,
                        fixture.staged_root,
                        fixture.manifest,
                        fixture.state_root,
                        fault_hook=hold_after_first,
                    )
                )
            )
            first.start()
            self.assertTrue(entered.wait(5))
            second = self.module.apply_source_transaction(
                fixture.skills_root,
                fixture.staged_root,
                fixture.manifest,
                fixture.state_root,
            )
            release.set()
            first.join(5)

            self.assertEqual(second["status"], "busy")
            self.assertEqual([result["status"] for result in results], ["updated"])

    def test_cli_uses_explicit_paths_and_requires_confirmation_before_write(self):
        with self.fixture() as fixture:
            command = [
                sys.executable,
                "-X",
                "utf8",
                str(UPDATER),
                "apply",
                "--skills-root",
                str(fixture.skills_root),
                "--staged-root",
                str(fixture.staged_root),
                "--manifest",
                str(fixture.root / "cached-manifest.json"),
                "--state-root",
                str(fixture.state_root),
                "--json",
            ]
            Path(fixture.root / "cached-manifest.json").write_text(
                json.dumps(fixture.manifest), encoding="utf-8"
            )
            before = snapshot_tree(fixture.skills_root)
            result = subprocess.run(
                command,
                cwd=fixture.root / "unrelated-working-directory",
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            ) if (fixture.root / "unrelated-working-directory").mkdir() is None else None
            self.assertIsNotNone(result)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "confirmation_required")
            self.assertEqual(snapshot_tree(fixture.skills_root), before)


class UpdateCheckTests(unittest.TestCase):
    def test_manifest_fetch_rejects_responses_over_the_size_limit(self):
        module = load_module(UPDATER, "legal_skills_update_manifest_size")

        class OversizedResponse:
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                self.requested_size = size
                return b"x" * (module.MAX_MANIFEST_BYTES + 1)

        response = OversizedResponse()
        with patch.object(module, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "size limit"):
                module.fetch_manifest(module.MANIFEST_URL, None)

        self.assertEqual(response.requested_size, module.MAX_MANIFEST_BYTES + 1)

    def test_fresh_cache_avoids_network_for_six_hours(self):
        module = load_module(UPDATER, "legal_skills_update")
        calls = []
        state = {
            "last_network_check": 1_000.0,
            "cached_manifest": make_manifest("1.0.0"),
            "etag": '"abc"',
        }
        with updater_fixture(state=state) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0 + 21_599,
                fetcher=lambda *args: calls.append(args),
            )
        self.assertEqual(result["status"], "cached")
        self.assertEqual(calls, [])

    def test_six_hour_boundary_fetches_and_finds_newer_version(self):
        module = load_module(UPDATER, "legal_skills_update_boundary")
        with updater_fixture(last_check=1_000.0) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0 + 21_600,
                fetcher=lambda *_: module.FetchResult(make_manifest("1.1.0"), '"new"', False),
            )
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["current_version"], "1.0.0")
        self.assertEqual(result["latest_version"], "1.1.0")

    def test_force_bypasses_a_fresh_cache(self):
        module = load_module(UPDATER, "legal_skills_update_force")
        calls = []
        state = {
            "last_network_check": 1_000.0,
            "cached_manifest": make_manifest("1.0.0"),
        }
        with updater_fixture(state=state) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                force=True,
                now=1_001.0,
                fetcher=lambda *args: (
                    calls.append(args),
                    module.FetchResult(make_manifest("1.1.0"), '"new"', False),
                )[1],
            )
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(len(calls), 1)

    def test_not_modified_reuses_cached_manifest(self):
        module = load_module(UPDATER, "legal_skills_update_not_modified")
        state = {
            "last_network_check": 1_000.0,
            "cached_manifest": make_manifest("1.1.0"),
            "etag": '"old"',
        }
        with updater_fixture(state=state) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0 + 21_600,
                fetcher=lambda *_: module.FetchResult(None, '"old"', True),
            )
            saved = json.loads(fixture.state_path.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["latest_version"], "1.1.0")
        self.assertEqual(saved["last_network_check"], 22_600.0)
        self.assertEqual(saved["etag"], '"old"')

    def test_offline_is_not_reported_as_up_to_date(self):
        module = load_module(UPDATER, "legal_skills_update_offline")
        with updater_fixture() as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=lambda *_: (_ for _ in ()).throw(OSError("offline")),
            )
        self.assertEqual(result["status"], "offline")
        self.assertFalse(result["fatal"])
        self.assertNotEqual(result["status"], "up_to_date")

    def test_offline_attempt_suppresses_another_automatic_fetch_for_six_hours(self):
        module = load_module(UPDATER, "legal_skills_update_offline_cache")
        calls = []

        def offline_fetcher(*_):
            calls.append("fetch")
            raise OSError("offline")

        with updater_fixture() as fixture:
            first = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=offline_fetcher,
            )
            second = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0 + 21_599,
                fetcher=offline_fetcher,
            )
            self.assertEqual(first["status"], "offline")
            self.assertEqual(second["status"], "offline")
            self.assertEqual(calls, ["fetch"])
            state = json.loads(fixture.state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["last_network_check"], 1_000.0)
            self.assertEqual(state["last_nonfatal_status"], "offline")

    def test_invalid_manifest_suppresses_another_automatic_fetch_for_six_hours(self):
        module = load_module(UPDATER, "legal_skills_update_invalid_cache")
        calls = []

        def invalid_fetcher(*_):
            calls.append("fetch")
            return module.FetchResult({"schema_version": 1}, '"bad"', False)

        with updater_fixture() as fixture:
            first = module.check_for_update(
                fixture.skill_dir,
                now=2_000.0,
                fetcher=invalid_fetcher,
            )
            second = module.check_for_update(
                fixture.skill_dir,
                now=2_000.0 + 21_599,
                fetcher=invalid_fetcher,
            )
            self.assertEqual(first["status"], "invalid_manifest")
            self.assertEqual(second["status"], "invalid_manifest")
            self.assertEqual(calls, ["fetch"])
            state = json.loads(fixture.state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["last_network_check"], 2_000.0)
            self.assertEqual(state["last_nonfatal_status"], "invalid_manifest")

    def test_non_string_archive_url_returns_nonfatal_invalid_manifest(self):
        module = load_module(UPDATER, "legal_skills_update_non_string_url")
        manifest = make_manifest("1.1.0")
        manifest["archive_url"] = {"host": "github.com"}

        with updater_fixture() as fixture:
            try:
                result = module.check_for_update(
                    fixture.skill_dir,
                    now=3_000.0,
                    fetcher=lambda *_: module.FetchResult(manifest, '"bad"', False),
                )
            except (AttributeError, TypeError) as exc:
                self.fail(f"check_for_update leaked archive_url type error: {exc}")

        self.assertEqual(result["status"], "invalid_manifest")
        self.assertFalse(result["fatal"])

    def test_save_state_replaces_a_complete_sibling_file_atomically(self):
        module = load_module(UPDATER, "legal_skills_update_atomic_state")
        with CanonicalTemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            module.save_state(path, {"etag": '"new"', "last_network_check": 123.0})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"etag": '"new"', "last_network_check": 123.0},
            )
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_state_root_uses_local_app_data_on_windows_and_xdg_on_posix(self):
        module = load_module(UPDATER, "legal_skills_update_state_roots")
        self.assertEqual(
            module.get_state_root(
                {"LOCALAPPDATA": r"C:\\Users\\Ada\\AppData\\Local"}, "win32"
            ),
            Path(r"C:\\Users\\Ada\\AppData\\Local") / "hermes-legal-research-skills",
        )
        self.assertEqual(
            module.get_state_root({"XDG_STATE_HOME": "/var/state", "HOME": "/home/ada"}, "linux"),
            Path("/var/state/hermes-legal-research-skills"),
        )
        self.assertEqual(
            module.get_state_root({"HOME": "/home/ada"}, "darwin"),
            Path("/home/ada/.local/state/hermes-legal-research-skills"),
        )

    def test_expired_snooze_allows_a_new_update_notice(self):
        module = load_module(UPDATER, "legal_skills_update_snooze_expiry")
        with updater_fixture(state={"snooze_until": 999.0}) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=lambda *_: module.FetchResult(make_manifest("1.1.0"), '"new"', False),
            )
        self.assertEqual(result["status"], "update_available")

    def test_ignored_current_version_suppresses_the_notice(self):
        module = load_module(UPDATER, "legal_skills_update_ignore")
        with updater_fixture(state={"ignored_version": "1.1.0"}) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=lambda *_: module.FetchResult(make_manifest("1.1.0"), '"new"', False),
            )
        self.assertEqual(result["status"], "ignored")

    def test_higher_version_after_ignored_version_is_announced(self):
        module = load_module(UPDATER, "legal_skills_update_higher_version")
        with updater_fixture(state={"ignored_version": "1.1.0"}) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=lambda *_: module.FetchResult(make_manifest("1.2.0"), '"new"', False),
            )
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["latest_version"], "1.2.0")

    def test_history_aggregates_cached_and_new_bundle_versions(self):
        module = load_module(UPDATER, "legal_skills_update_history")
        cached = make_manifest("1.0.0")
        incoming = make_manifest(
            "1.1.0",
            history=[
                {
                    "bundle_version": "0.9.0",
                    "published_at": "2026-08-01T00:00:00+08:00",
                    "update_level": "feature",
                    "summary": "Bundle 0.9.0",
                    "changes": ["Change 0.9.0"],
                },
                *cached["history"],
                {
                    "bundle_version": "1.1.0",
                    "published_at": "2026-08-10T00:00:00+08:00",
                    "update_level": "feature",
                    "summary": "Bundle 1.1.0",
                    "changes": ["Change 1.1.0"],
                },
            ],
        )
        with updater_fixture(state={"cached_manifest": cached}) as fixture:
            result = module.check_for_update(
                fixture.skill_dir,
                now=1_000.0,
                fetcher=lambda *_: module.FetchResult(incoming, '"new"', False),
            )
            details = module.details(fixture.skill_dir)
        self.assertEqual(
            [entry["bundle_version"] for entry in result["history"]],
            ["0.9.0", "1.0.0", "1.1.0"],
        )
        self.assertEqual(details["history"], result["history"])

    def test_cli_state_actions_emit_json_without_touching_skill_directory(self):
        with updater_fixture() as fixture:
            before = sorted(path.relative_to(fixture.skill_dir) for path in fixture.skill_dir.rglob("*"))
            base_command = [sys.executable, "-X", "utf8", str(UPDATER)]
            env = dict(os.environ)
            env["LOCALAPPDATA"] = str(fixture.root / "state-base")
            env["XDG_STATE_HOME"] = str(fixture.root / "state-base")
            env["HOME"] = str(fixture.root / "isolated-home")
            snoozed = subprocess.run(
                [*base_command, "snooze", "--hours", "2", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=fixture.skill_dir,
                env=env,
                check=False,
            )
            ignored = subprocess.run(
                [*base_command, "ignore", "1.1.0", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=fixture.skill_dir,
                env=env,
                check=False,
            )
            detailed = subprocess.run(
                [*base_command, "details", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=fixture.skill_dir,
                env=env,
                check=False,
            )
            after = sorted(path.relative_to(fixture.skill_dir) for path in fixture.skill_dir.rglob("*"))
        self.assertEqual(snoozed.returncode, 0, snoozed.stderr)
        self.assertEqual(ignored.returncode, 0, ignored.stderr)
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        self.assertIn("snooze_until", json.loads(snoozed.stdout))
        self.assertEqual(json.loads(ignored.stdout)["ignored_version"], "1.1.0")
        self.assertIn("history", json.loads(detailed.stdout))
        self.assertEqual(before, after)

    def test_check_gracefully_degrades_when_lock_dir_is_unwritable(self):
        module = load_module(UPDATER, "legal_skills_update_lock_perm")
        with updater_fixture() as fixture:
            def failing_fetcher(*args, **kwargs):
                raise OSError("network disabled in sandbox")

            def failing_lock(path):
                raise PermissionError(1, f"Operation not permitted: '{path}'")

            with patch.object(module, "operation_lock", side_effect=failing_lock):
                result = module.check_for_update(
                    fixture.skill_dir,
                    force=True,
                    fetcher=failing_fetcher,
                )
            self.assertEqual(result["status"], "offline")
            self.assertFalse(result["fatal"])
            self.assertIn("network disabled in sandbox", result.get("message", ""))

    def test_detect_install_context_recognizes_antigravity_plugin_path(self):
        module = load_module(UPDATER, "legal_skills_update_antigravity_channel")
        with CanonicalTemporaryDirectory() as tmp:
            plugin_root = (
                Path(tmp)
                / ".gemini"
                / "config"
                / "plugins"
                / "legal-academic-research-skills"
                / "skills"
                / "law-paper-writing"
            )
            plugin_root.mkdir(parents=True)
            (plugin_root / "bundle-lock.json").write_text(
                json.dumps({"bundle_version": "1.0.0"}), encoding="utf-8"
            )
            self.assertTrue(module.is_antigravity_plugin_path(plugin_root))
            result = module.check_for_update(
                plugin_root,
                fetcher=lambda *_: module.FetchResult(make_manifest("1.0.0"), '"etag"', False),
            )
            self.assertEqual(result["update_channel"], "antigravity-plugin")
            with self.assertRaises(module.ArchiveError) as ctx:
                module.detect_installation_mode(plugin_root, ["law-paper-writing"])
            self.assertIn("Antigravity plugin", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

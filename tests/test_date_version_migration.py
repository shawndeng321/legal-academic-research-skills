from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_bundle_updater import (
    CanonicalTemporaryDirectory,
    PREPARE, SKILLS, UPDATER, load_module, make_manifest, sha256_bytes,
    snapshot_tree, write_installation, write_staged_bundle,
    write_hermes_lock,
    make_hermes_lock,
    run_prepare, write_skill,
)


OLD_NAME = "chinese-law-paper-writing"
NEW_NAME = "law-paper-writing"


def canonical_manifest(version: str = "2610.9.0") -> dict:
    manifest = make_manifest(version)
    manifest["skills"] = {
        NEW_NAME if name == OLD_NAME else name: version
        for name in manifest["skills"]
    }
    manifest["files"] = {
        path.replace(OLD_NAME + "/", NEW_NAME + "/", 1): digest
        for path, digest in manifest["files"].items()
    }
    return manifest


def date_bundle(version: str = "2610.9.0") -> tuple[dict, dict[str, bytes]]:
    manifest = canonical_manifest(version)
    files = {}
    for name in SKILLS:
        content = {
            "SKILL.md": f"incoming {name}\n".encode(),
            "agents/openai.yaml": f"incoming agent {name}\n".encode(),
        }
        lock = {
            "schema_version": 1, "bundle_id": manifest["bundle_id"],
            "bundle_version": version, "skill_name": name,
            "skill_version": version,
            "files": {relative: sha256_bytes(data) for relative, data in content.items()},
        }
        content["bundle-lock.json"] = (json.dumps(lock) + "\n").encode()
        files.update({f"{name}/{relative}": data for relative, data in content.items()})
    manifest["files"] = {path: sha256_bytes(data) for path, data in files.items()}
    return manifest, files


@contextmanager
def migration_fixture(category: str | None = None):
    with CanonicalTemporaryDirectory() as tmp:
        root = Path(tmp)
        installed = root / "skills"
        installed.mkdir()
        write_installation(installed)
        original = installed / NEW_NAME
        if category:
            parent = installed / category
            parent.mkdir()
        else:
            parent = installed
        original.rename(parent / OLD_NAME)
        old_path = parent / OLD_NAME
        lock_path = old_path / "bundle-lock.json"
        lock = json.loads(lock_path.read_bytes())
        lock.update(skill_name=OLD_NAME, skill_version="6.0.1", bundle_version="2026.0928.0")
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        unrelated = installed / "other-skill" / "SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_bytes(b"untouched unrelated skill\n")
        material = installed / "raw" / "private-research.pdf"
        material.parent.mkdir()
        material.write_bytes(b"\x00untouched research material\xff")
        manifest, files = date_bundle()
        staged = root / "staged"
        write_staged_bundle(staged, manifest, files)
        yield SimpleNamespace(
            root=root, skills_root=installed, staged_root=staged,
            state_root=root / "state", manifest=manifest, files=files,
            old_path=old_path, new_path=parent / NEW_NAME,
        )


class SourceRenameTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(UPDATER, f"source_rename_{self._testMethodName}")

    def test_renames_old_source_copy_without_treating_identity_as_local_edit(self):
        with migration_fixture() as fixture:
            before = snapshot_tree(fixture.old_path)
            result = self.module.apply_source_transaction(
                fixture.skills_root, fixture.staged_root,
                fixture.manifest, fixture.state_root,
            )
            self.assertEqual(result["status"], "updated", result)
            self.assertEqual(result["report"]["status"], "clean")
            self.assertFalse(fixture.old_path.exists())
            lock = json.loads((fixture.new_path / "bundle-lock.json").read_bytes())
            self.assertEqual(lock["skill_name"], NEW_NAME)
            self.assertEqual(lock["bundle_version"], "2610.9.0")
            backup = Path(result["backup_path"])
            self.assertEqual(snapshot_tree(backup / OLD_NAME), before)
            transaction = json.loads((backup / "transaction.json").read_bytes())
            self.assertEqual(Path(transaction["skill_paths"][NEW_NAME]), fixture.old_path)
            self.assertEqual(Path(transaction["target_paths"][NEW_NAME]), fixture.new_path)
            self.assertEqual((fixture.skills_root / "other-skill/SKILL.md").read_bytes(), b"untouched unrelated skill\n")
            self.assertEqual((fixture.skills_root / "raw/private-research.pdf").read_bytes(), b"\x00untouched research material\xff")

    def test_failure_restores_old_name_and_exact_bytes_in_original_parent(self):
        for category in (None, "writing"):
            for failed_name in SKILLS:
                with self.subTest(category=category, fault=failed_name), migration_fixture(category) as fixture:
                    before = snapshot_tree(fixture.skills_root)

                    def fail_after_skill(name):
                        if name == failed_name:
                            raise RuntimeError("injected migration failure")

                    result = self.module.apply_source_transaction(
                        fixture.skills_root, fixture.staged_root,
                        fixture.manifest, fixture.state_root,
                        fault_hook=fail_after_skill,
                    )
                    self.assertEqual(result["status"], "rolled_back", result)
                    self.assertEqual(snapshot_tree(fixture.skills_root), before)
                    self.assertTrue(fixture.old_path.is_dir())
                    self.assertFalse(fixture.new_path.exists())
                    transaction = json.loads((Path(result["backup_path"]) / "transaction.json").read_bytes())
                    self.assertEqual(transaction["status"], "rolled_back")

    def test_category_migration_stays_in_same_parent(self):
        with migration_fixture("writing") as fixture:
            result = self.module.apply_source_transaction(
                fixture.skills_root, fixture.staged_root,
                fixture.manifest, fixture.state_root,
            )
            self.assertEqual(result["status"], "updated", result)
            self.assertFalse(fixture.old_path.exists())
            self.assertTrue(fixture.new_path.is_dir())
            self.assertFalse((fixture.skills_root / NEW_NAME).exists())

    def test_legacy_local_changes_and_missing_skill_confirmations_are_independent(self):
        with migration_fixture("writing") as fixture:
            (fixture.old_path / "SKILL.md").write_bytes(b"my local writing edit\n")
            shutil.rmtree(fixture.skills_root / SKILLS[1])
            before = snapshot_tree(fixture.skills_root)
            for flags in ({}, {"allow_local_changes": True}, {"install_missing": True}):
                with self.subTest(flags=flags):
                    result = self.module.apply_source_transaction(
                        fixture.skills_root, fixture.staged_root,
                        fixture.manifest, fixture.state_root, **flags,
                    )
                    self.assertEqual(result["status"], "confirmation_required", result)
                    self.assertEqual(result["report"]["modified"], [NEW_NAME + "/SKILL.md"])
                    self.assertEqual(result["report"]["missing_skills"], [SKILLS[1]])
                    self.assertEqual(snapshot_tree(fixture.skills_root), before)
            result = self.module.apply_source_transaction(
                fixture.skills_root, fixture.staged_root,
                fixture.manifest, fixture.state_root,
                allow_local_changes=True, install_missing=True,
            )
            self.assertEqual(result["status"], "updated", result)
            self.assertEqual(snapshot_tree(Path(result["backup_path"]) / OLD_NAME)["SKILL.md"], b"my local writing edit\n")

    def test_old_new_conflict_stops_before_state_write(self):
        for old_category, new_category in ((None, None), ("writing", None), (None, "writing"), ("writing", "other")):
            with self.subTest(old=old_category, new=new_category), migration_fixture(old_category) as fixture:
                new_parent = fixture.skills_root / new_category if new_category else fixture.skills_root
                new_parent.mkdir(exist_ok=True)
                shutil.copytree(fixture.old_path, new_parent / NEW_NAME)
                before = snapshot_tree(fixture.skills_root)
                result = self.module.apply_source_transaction(
                    fixture.skills_root, fixture.staged_root,
                    fixture.manifest, fixture.state_root,
                    allow_local_changes=True, install_missing=True,
                )
                self.assertEqual(result["status"], "rejected", result)
                self.assertEqual(snapshot_tree(fixture.skills_root), before)
                self.assertFalse(fixture.state_root.exists())

    def test_fresh_canonical_installation_requires_install_missing(self):
        with migration_fixture() as fixture:
            shutil.rmtree(fixture.old_path)
            for name in SKILLS[1:]:
                shutil.rmtree(fixture.skills_root / name)
            result = self.module.apply_source_transaction(
                fixture.skills_root, fixture.staged_root,
                fixture.manifest, fixture.state_root,
            )
            self.assertEqual(result["status"], "confirmation_required", result)
            self.assertEqual(result["report"]["missing_skills"], sorted(SKILLS))
            result = self.module.apply_source_transaction(
                fixture.skills_root, fixture.staged_root,
                fixture.manifest, fixture.state_root, install_missing=True,
            )
            self.assertEqual(result["status"], "updated", result)
            self.assertFalse(fixture.old_path.exists())
            self.assertTrue((fixture.skills_root / NEW_NAME).is_dir())

    def test_replace_error_after_migration_move_removes_new_name_on_rollback(self):
        with migration_fixture() as fixture:
            before = snapshot_tree(fixture.skills_root)
            replace = self.module.os.replace

            def fail_after_move(source, destination):
                replace(source, destination)
                if Path(destination) == fixture.new_path:
                    raise OSError("injected error after directory move")

            with patch.object(self.module.os, "replace", side_effect=fail_after_move):
                result = self.module.apply_source_transaction(
                    fixture.skills_root, fixture.staged_root,
                    fixture.manifest, fixture.state_root,
                )
            self.assertEqual(result["status"], "rolled_back", result)
            self.assertEqual(snapshot_tree(fixture.skills_root), before)
            self.assertFalse(fixture.new_path.exists())

    def test_unsafe_legacy_path_is_rejected_before_any_state_write(self):
        for unsafe in ("skill-symlink", "category-symlink", "skill-worktree", "category-worktree", "ancestor-worktree", "state-parent-symlink"):
            with self.subTest(unsafe=unsafe), migration_fixture("writing") as fixture:
                if unsafe == "skill-symlink":
                    moved = fixture.root / "outside-skill"
                    fixture.old_path.rename(moved)
                    fixture.old_path.symlink_to(moved, target_is_directory=True)
                elif unsafe == "category-symlink":
                    category = fixture.old_path.parent
                    moved = fixture.root / "outside-category"
                    category.rename(moved)
                    category.symlink_to(moved, target_is_directory=True)
                elif unsafe == "state-parent-symlink":
                    state = fixture.root / "external-state"
                    state.mkdir()
                    linked = fixture.root / "state-link"
                    linked.symlink_to(state, target_is_directory=True)
                    fixture.state_root = linked / "bundle-state"
                else:
                    parent = {
                        "skill-worktree": fixture.old_path,
                        "category-worktree": fixture.old_path.parent,
                        "ancestor-worktree": fixture.root,
                    }[unsafe]
                    (parent / ".git").write_bytes(b"gitdir: safe-test-worktree\n")
                result = self.module.apply_source_transaction(
                    fixture.skills_root, fixture.staged_root,
                    fixture.manifest, fixture.state_root,
                    allow_local_changes=True, install_missing=True,
                )
                self.assertEqual(result["status"], "rejected", result)
                self.assertFalse(fixture.state_root.exists())

    def test_final_journal_write_failure_rolls_back_migration(self):
        with migration_fixture("writing") as fixture:
            before = snapshot_tree(fixture.skills_root)
            write_transaction = self.module._write_transaction

            def fail_success_journal(path, transaction):
                if transaction["status"] == "updated":
                    raise OSError("injected success journal write failure")
                write_transaction(path, transaction)

            with patch.object(self.module, "_write_transaction", side_effect=fail_success_journal):
                result = self.module.apply_source_transaction(
                    fixture.skills_root, fixture.staged_root,
                    fixture.manifest, fixture.state_root,
                )
            self.assertEqual(result["status"], "rolled_back", result)
            self.assertEqual(snapshot_tree(fixture.skills_root), before)
            self.assertFalse(fixture.new_path.exists())

    def test_new_cli_bootstraps_legacy_install_then_performs_normal_date_upgrade(self):
        with migration_fixture("writing") as fixture:
            before = snapshot_tree(fixture.old_path)

            def cli(command, *flags):
                completed = subprocess.run([
                    sys.executable, "-B", str(UPDATER), command,
                    "--skills-root", str(fixture.skills_root),
                    "--staged-root", str(fixture.staged_root),
                    "--manifest", str(fixture.staged_root / "bundle-release.json"),
                    "--state-root", str(fixture.state_root), "--json", *flags,
                ], cwd=fixture.root, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            preview = cli("diff")
            self.assertEqual(preview["status"], "clean", preview)
            self.assertIn("-local paper", preview["diff"])
            blocked = cli("apply")
            self.assertEqual(blocked["status"], "confirmation_required", blocked)
            self.assertFalse(fixture.state_root.exists())
            migrated = cli("apply", "--allow-local-changes")
            self.assertEqual(migrated["status"], "updated", migrated)
            self.assertFalse(fixture.old_path.exists())
            self.assertTrue(fixture.new_path.is_dir())
            self.assertEqual(snapshot_tree(Path(migrated["backup_path"]) / OLD_NAME), before)
            self.assertTrue((fixture.state_root / "worker" / UPDATER.name).is_file())

            shutil.rmtree(fixture.staged_root)
            manifest, files = date_bundle("2610.9.1")
            write_staged_bundle(fixture.staged_root, manifest, files)
            upgraded = cli("apply", "--allow-local-changes")
            self.assertEqual(upgraded["status"], "updated", upgraded)
            self.assertEqual(upgraded["report"]["status"], "clean")
            self.assertFalse(fixture.old_path.exists())
            for name, path in self.module.resolve_skill_dirs(fixture.skills_root).items():
                lock = json.loads((path / "bundle-lock.json").read_bytes())
                self.assertEqual(lock["skill_name"], name)
                self.assertEqual(lock["bundle_version"], "2610.9.1")


class ManifestMigrationTests(unittest.TestCase):
    def test_new_canonical_manifest_is_accepted_without_rewriting_identity(self):
        module = load_module(UPDATER, "canonical_manifest_migration")
        manifest = canonical_manifest()
        try:
            checked = module.validate_manifest(manifest)
        except ValueError as exc:
            self.fail(f"canonical release rejected: {exc}")
        self.assertEqual(checked, manifest)

    def test_only_canonical_skill_set_can_be_staged_for_apply(self):
        module = load_module(UPDATER, "staged_canonical_identity")
        for noncanonical in ("legacy-manifest", "empty-old-alias-directory"):
            with self.subTest(noncanonical=noncanonical), migration_fixture() as fixture:
                if noncanonical == "legacy-manifest":
                    manifest = legacy_manifest("2610.9.0")
                    files = {
                        path.replace(NEW_NAME + "/", OLD_NAME + "/", 1): content
                        for path, content in fixture.files.items()
                    }
                    manifest["files"] = {path: sha256_bytes(content) for path, content in files.items()}
                    shutil.rmtree(fixture.staged_root)
                    write_staged_bundle(fixture.staged_root, manifest, files)
                    self.assertEqual(module.validate_manifest(manifest), manifest)
                    fixture.manifest = manifest
                else:
                    (fixture.staged_root / OLD_NAME).mkdir()
                before = snapshot_tree(fixture.skills_root)
                result = module.apply_source_transaction(
                    fixture.skills_root, fixture.staged_root,
                    fixture.manifest, fixture.state_root,
                )
                self.assertEqual(result["status"], "rejected", result)
                self.assertEqual(snapshot_tree(fixture.skills_root), before)
                self.assertFalse(fixture.state_root.exists())

    def test_new_cli_check_reads_old_schema_one_manifest_against_explicit_old_path(self):
        for current, latest, status in (
            ("2026.0928.0", "2026.0928.0", "up_to_date"),
            ("2610.9.0", "2026.0928.0", "up_to_date"),
            ("2610.9.0", "2026.1228.0", "update_available"),
        ):
            with self.subTest(current=current, latest=latest), migration_fixture() as fixture:
                lock_path = fixture.old_path / "bundle-lock.json"
                lock = json.loads(lock_path.read_bytes())
                lock["bundle_version"] = current
                lock_path.write_text(json.dumps(lock), encoding="utf-8")
                manifest_path = fixture.root / "legacy-baseline.json"
                manifest_path.write_text(json.dumps(legacy_manifest(latest)), encoding="utf-8")
                before = snapshot_tree(fixture.skills_root)
                completed = subprocess.run([
                    sys.executable, "-B", str(UPDATER), "check",
                    "--skill-dir", str(fixture.old_path),
                    "--manifest", str(manifest_path),
                    "--state-root", str(fixture.state_root), "--json",
                ], cwd=fixture.root, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["status"], status, result)
                self.assertEqual(result["current_version"], current)
                self.assertEqual(result["latest_version"], latest)
                self.assertEqual(snapshot_tree(fixture.skills_root), before)


class HermesRenameTests(unittest.TestCase):
    def test_locked_hub_worker_rechecks_a_concurrently_added_legacy_entry(self):
        module = load_module(UPDATER, "hub_migration_locked_recheck")
        with migration_fixture() as fixture:
            fixture.old_path.rename(fixture.new_path)
            lock_path = fixture.skills_root / ".hub" / "lock.json"
            hub_lock = make_hermes_lock(fixture.skills_root)
            write_hermes_lock(lock_path, hub_lock)
            before_skills = {
                name: snapshot_tree(fixture.skills_root / name) for name in SKILLS
            }

            @contextmanager
            def add_old_entry_before_lock_yields(_path):
                changed = json.loads(lock_path.read_bytes())
                changed["installed"][OLD_NAME] = {"install_path": OLD_NAME}
                write_hermes_lock(lock_path, changed)
                yield

            with patch.object(module, "operation_lock", add_old_entry_before_lock_yields):
                result = module.apply_hermes_transaction(
                    fixture.skills_root, lock_path,
                    fixture.manifest, fixture.state_root,
                    allow_local_changes=True,
                    runner=lambda *_args, **_kwargs: self.fail("no update command may run after Hub identity changes"),
                )
            self.assertEqual(result["status"], "migration_required", result)
            self.assertEqual({name: snapshot_tree(fixture.skills_root / name) for name in SKILLS}, before_skills)
            self.assertIn(OLD_NAME, json.loads(lock_path.read_bytes())["installed"])
            self.assertFalse((fixture.state_root / "backups").exists())

    def test_old_hub_entry_requires_one_time_migration_before_any_write(self):
        module = load_module(UPDATER, "hub_name_migration")
        for adapter in ("hub", "source"):
            with self.subTest(adapter=adapter), migration_fixture() as fixture:
                lock_path = fixture.skills_root / ".hub" / "lock.json"
                write_hermes_lock(lock_path, {
                    "version": 1, "installed": {
                        OLD_NAME: {
                            "source": "github", "install_path": OLD_NAME,
                            "identifier": "shawndeng321/legal-academic-research-skills/" + OLD_NAME,
                        },
                        "other-skill": {"unchanged": "do not alter this entry"},
                    },
                })
                before = snapshot_tree(fixture.skills_root)
                if adapter == "hub":
                    result = module.apply_hermes_transaction(
                        fixture.skills_root, lock_path,
                        fixture.manifest, fixture.state_root,
                        allow_local_changes=True,
                        runner=lambda *_args, **_kwargs: self.fail("old-name update command must never run"),
                    )
                else:
                    result = module.apply_source_transaction(
                        fixture.skills_root, fixture.staged_root,
                        fixture.manifest, fixture.state_root,
                        allow_local_changes=True, install_missing=True,
                    )
                self.assertEqual(result["status"], "migration_required", result)
                self.assertIn("one-time", result["message"])
                self.assertEqual(snapshot_tree(fixture.skills_root), before)
                self.assertEqual(snapshot_tree(fixture.staged_root), {
                    "bundle-release.json": (fixture.staged_root / "bundle-release.json").read_bytes(),
                    **fixture.files,
                })
                self.assertFalse(fixture.state_root.exists())

    def test_cli_never_copies_worker_for_old_hub_migration(self):
        with migration_fixture("writing") as fixture:
            lock_path = fixture.skills_root / ".hub" / "lock.json"
            write_hermes_lock(lock_path, {"version": 1, "installed": {OLD_NAME: {"install_path": "writing/" + OLD_NAME}}})
            before = snapshot_tree(fixture.skills_root)
            completed = subprocess.run([
                sys.executable, "-B", str(UPDATER), "apply",
                "--skills-root", str(fixture.skills_root),
                "--staged-root", str(fixture.staged_root),
                "--manifest", str(fixture.staged_root / "bundle-release.json"),
                "--state-root", str(fixture.state_root),
                "--allow-local-changes", "--install-missing", "--json",
            ], cwd=fixture.root, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "migration_required")
            self.assertEqual(snapshot_tree(fixture.skills_root), before)
            self.assertFalse(fixture.state_root.exists())


class DateVersionTests(unittest.TestCase):
    def test_date_comparison_orders_old_date_line_and_same_day_revision(self):
        module = load_module(UPDATER, "date_version_ordering")
        cases = (
            ("2026.0928.0", "2609.28.0", "up_to_date"),
            ("2026.0928.0", "2610.9.0", "update_available"),
            ("2610.9.0", "2026.1228.0", "update_available"),
            ("2610.9.0", "2610.9.1", "update_available"),
            ("2610.9.1", "2610.10.0", "update_available"),
            ("2610.10.0", "2610.9.1", "up_to_date"),
            ("6.0.1", "2610.9.0", "update_available"),
        )
        for current, latest, status in cases:
            with self.subTest(current=current, latest=latest):
                result = module._status_for_manifest(
                    current, canonical_manifest(latest), {}, 1000.0, []
                )
                self.assertEqual(result["status"], status)
        entries = [{"bundle_version": version} for version in (
            "2026.1228.0", "2610.9.1", "2610.9.0", "2026.0928.0", "6.0.1"
        )]
        self.assertEqual(
            [entry["bundle_version"] for entry in module._aggregate_history(entries)],
            ["6.0.1", "2026.0928.0", "2610.9.0", "2610.9.1", "2026.1228.0"],
        )
        self.assertEqual(module.parse_semver("2026.0928.0"), (2026, 928, 0))
        self.assertEqual(module.parse_semver("6.0.1"), (6, 0, 1))


def date_release_repository(root: Path, version: str = "2610.9.0") -> None:
    tool = root / "tools" / "prepare_bundle_release.py"
    tool.parent.mkdir()
    shutil.copy2(PREPARE, tool)
    for name in SKILLS:
        write_skill(root, name, version)


def write_date_release(root: Path, version: str = "2610.9.0"):
    return run_prepare(
        root, "--write", "--bundle-version", version,
        "--published-at", "2026-10-09T00:00:00+08:00",
        "--update-level", "feature", "--summary", "date release",
        "--change", "canonical writing identity",
    )


def legacy_manifest(version: str = "2026.0928.0") -> dict:
    manifest = make_manifest(version)
    manifest["skills"] = {
        OLD_NAME if name == NEW_NAME else name: skill_version
        for name, skill_version in manifest["skills"].items()
    }
    manifest["files"] = {
        path.replace(NEW_NAME + "/", OLD_NAME + "/", 1): digest
        for path, digest in manifest["files"].items()
    }
    return manifest


def legacy_release_repository(root: Path) -> dict:
    tool = root / "tools" / "prepare_bundle_release.py"
    tool.parent.mkdir()
    shutil.copy2(PREPARE, tool)
    prepare = load_module(PREPARE, "legacy_release_fixture_prepare")
    manifest = legacy_manifest()
    files = {}
    for name, version in manifest["skills"].items():
        skill = write_skill(root, name, version)
        lock = prepare.build_lock(name, version, manifest["bundle_version"], prepare.collect_skill_files(skill))
        (skill / "bundle-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        for path in skill.rglob("*"):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = sha256_bytes(path.read_bytes())
    manifest["files"] = files
    (root / "bundle-release.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


class ReleaseDateTests(unittest.TestCase):
    def test_new_release_rejects_legacy_alias_or_symlinked_skill_before_writing(self):
        for unsafe in ("old-alias", "symlinked-skill"):
            with self.subTest(unsafe=unsafe), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                date_release_repository(root)
                if unsafe == "old-alias":
                    (root / OLD_NAME).mkdir()
                else:
                    actual = root / "actual-writing"
                    (root / NEW_NAME).rename(actual)
                    (root / NEW_NAME).symlink_to(actual, target_is_directory=True)
                before = snapshot_tree(root)
                result = write_date_release(root)
                self.assertNotEqual(result.returncode, 0, "unsafe release was generated")
                self.assertEqual(snapshot_tree(root), before)

    def test_invalid_calendar_version_is_rejected_before_writing_locks(self):
        invalid = ("2613.9.0", "2610.0.0", "2610.32.0", "2602.29.0", "2610.999.0")
        for version in invalid:
            with self.subTest(version=version), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                date_release_repository(root, version)
                before = snapshot_tree(root)
                result = write_date_release(root, version)
                self.assertNotEqual(result.returncode, 0, "illegal calendar release was generated")
                self.assertEqual(snapshot_tree(root), before)
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            date_release_repository(root, "2402.29.0")
            self.assertEqual(write_date_release(root, "2402.29.0").returncode, 0)
            self.assertEqual(run_prepare(root, "--check").returncode, 0)

    def test_date_release_requires_all_three_skill_versions_to_equal_bundle_version(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            date_release_repository(root)
            skill_md = root / SKILLS[1] / "SKILL.md"
            skill_md.write_text(skill_md.read_text().replace("2610.9.0", "5.0.1"), encoding="utf-8")
            before = snapshot_tree(root)
            result = write_date_release(root)
            self.assertNotEqual(result.returncode, 0, "mixed version date release was generated")
            self.assertEqual(snapshot_tree(root), before)
        for version in ("2610.9.0", "2610.10.0", "2610.9.1"):
            with self.subTest(version=version), CanonicalTemporaryDirectory() as tmp:
                root = Path(tmp)
                date_release_repository(root, version)
                result = write_date_release(root, version)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((root / "bundle-release.json").read_bytes())
                self.assertEqual(manifest["skills"], dict.fromkeys(SKILLS, version))
                self.assertEqual(manifest["bundle_version"], version)
                self.assertEqual(run_prepare(root, "--check").returncode, 0)

    def test_generator_check_accepts_legacy_schema_one_baseline_without_rewriting(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_release_repository(root)
            before = snapshot_tree(root)
            result = run_prepare(root, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Bundle 2026.0928.0 is consistent", result.stdout)
            self.assertEqual(snapshot_tree(root), before)
            (root / OLD_NAME / "SKILL.md").write_bytes(b"tampered legacy content\n")
            self.assertNotEqual(run_prepare(root, "--check").returncode, 0)

    def test_new_write_uses_canonical_tree_versions_not_legacy_manifest_skill_map(self):
        with CanonicalTemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = legacy_release_repository(root)
            (root / OLD_NAME).rename(root / NEW_NAME)
            for name in SKILLS:
                old_name = OLD_NAME if name == NEW_NAME else name
                skill_md = root / name / "SKILL.md"
                text = skill_md.read_text(encoding="utf-8")
                text = text.replace(previous["skills"][old_name], "2610.9.0")
                text = text.replace(OLD_NAME, NEW_NAME)
                skill_md.write_text(text, encoding="utf-8")
            result = write_date_release(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((root / "bundle-release.json").read_bytes())
            self.assertEqual(manifest["skills"], dict.fromkeys(SKILLS, "2610.9.0"))
            self.assertEqual([entry["bundle_version"] for entry in manifest["history"]], ["2026.0928.0", "2610.9.0"])
            self.assertEqual(run_prepare(root, "--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()

"""Offline behavior tests: fake GitHub responses, real isolated Git repositories."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/pr-green/scripts/pr-green"
loader = importlib.machinery.SourceFileLoader("pr_green", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
pg = importlib.util.module_from_spec(spec)
loader.exec_module(pg)


def pr(**changes):
    return dict(dict(number=7, url="https://github.com/o/r/pull/7", state="OPEN", isDraft=False,
                     title="Fix thing", body="Evidence", headRefName="feature", headRefOid="head",
                     baseRefName="main", baseRefOid="base", headRepository={"name": "r"},
                     headRepositoryOwner={"login": "o"}, mergeable="MERGEABLE",
                     mergeStateStatus="CLEAN", reviewDecision="APPROVED"), **changes)


def upsert_args(**changes):
    return SimpleNamespace(**dict(dict(title_file=None, body_file=None, keep_draft=False), **changes))


def check(bucket="pass", **changes):
    return dict(dict(name="test", bucket=bucket, state="SUCCESS", workflow="CI",
                     link="https://github.com/o/r/actions/runs/42/job/3"), **changes)


class ReadinessTests(unittest.TestCase):
    def classify(self, **changes):
        args = dict(pr=pr(), rows=[check()], unresolved=[], local="head", base="base",
                    remote="head", contains_base=True, dirty=False)
        args.update(changes)
        return pg.classify(**args)[0]

    def test_ready_requires_full_contract(self):
        self.assertEqual(self.classify(), "READY")
        cases = [dict(local="unpublished"), dict(remote="other"), dict(base="new-base"),
                 dict(contains_base=False), dict(dirty=True), dict(unresolved=[{}]),
                 dict(pr=pr(isDraft=True)), dict(pr=pr(mergeable="CONFLICTING"))]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.classify(**case), "ACTION")

    def test_all_checks_include_optional_failures_and_cancellations(self):
        for bucket in ("fail", "cancel"):
            self.assertEqual(self.classify(rows=[check(), check(bucket)]), "ACTION")
        for bucket in ("pending", "new-unknown-state"):
            self.assertEqual(self.classify(rows=[check(bucket)]), "WAITING")

    def test_skipped_neutral_and_no_checks_follow_github_gate(self):
        self.assertEqual(self.classify(rows=[check("skipping"), check(state="NEUTRAL")]), "READY")
        self.assertEqual(self.classify(rows=[]), "READY")
        self.assertEqual(self.classify(rows=[], pr=pr(mergeStateStatus="BLOCKED")), "BLOCKED")

    def test_review_and_closed_pr_never_ready(self):
        for review in ("CHANGES_REQUESTED", "REVIEW_REQUIRED"):
            self.assertEqual(self.classify(pr=pr(reviewDecision=review)), "BLOCKED")
        for state in ("CLOSED", "MERGED"):
            self.assertEqual(self.classify(pr=pr(state=state)), "BLOCKED")
        for state in ("BLOCKED", "UNSTABLE", "HAS_HOOKS", "unexpected"):
            self.assertEqual(self.classify(pr=pr(mergeStateStatus=state)), "BLOCKED")
        self.assertEqual(self.classify(pr=pr(mergeStateStatus="UNKNOWN")), "WAITING")

    def test_actionable_work_precedes_approval_block(self):
        self.assertEqual(self.classify(pr=pr(reviewDecision="REVIEW_REQUIRED"), rows=[check("fail")]), "ACTION")

    def test_unknown_review_decision_cannot_report_ready(self):
        self.assertEqual(self.classify(pr=pr(reviewDecision="NEW_REQUIREMENT")), "BLOCKED")
        for decision in ("", None):
            self.assertEqual(self.classify(pr=pr(reviewDecision=decision)), "READY")

    def test_snapshot_rejects_head_or_metadata_races(self):
        for changed in (pr(headRefOid="new"), pr(body="new attestation"), pr(reviewDecision="CHANGES_REQUESTED")):
            ctx = SimpleNamespace(view=Mock(side_effect=[pr(), changed]), fetch=Mock(return_value=("base", "head")))
            with patch.object(pg, "current_branch"), patch.object(pg, "checks", return_value=[check()]), \
                 patch.object(pg, "threads", return_value=[]):
                self.assertEqual(pg.snapshot(ctx)[0], "WAITING")


class GithubTests(unittest.TestCase):
    def test_paginated_threads_include_outdated_and_second_page(self):
        def page(nodes, more, cursor):
            return {"repository": {"pullRequest": {"reviewThreads": {
                "nodes": nodes, "pageInfo": {"hasNextPage": more, "endCursor": cursor}}}}}
        ctx = SimpleNamespace(slug="o/r", pr=pr(), graphql=Mock(side_effect=[
            page([dict(id="resolved", isResolved=True)], True, "cursor1"),
            page([dict(id="old", isResolved=False, isOutdated=True)], False, None)]))
        self.assertEqual(pg.threads(ctx)[0]["id"], "old")
        self.assertEqual(ctx.graphql.call_args.kwargs["cursor"], "cursor1")

    def test_pagination_failure_is_not_empty_success(self):
        data = {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": None}}}}}
        with self.assertRaises(pg.Stop):
            pg.threads(SimpleNamespace(slug="o/r", pr=pr(), graphql=Mock(return_value=data)))

    def test_checks_no_checks_vs_auth_failure(self):
        ctx = SimpleNamespace(pr=pr(), selector="https://github.com/o/r")
        with patch.object(pg, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="no checks reported on branch")):
            self.assertEqual(pg.checks(ctx), [])
        with patch.object(pg, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="authentication failed")):
            with self.assertRaises(pg.Stop):
                pg.checks(ctx)

    def test_runs_are_scoped_to_host_and_repo(self):
        ctx = SimpleNamespace(host="github.com", slug="o/r")
        self.assertEqual(pg.actions_run_id(ctx, check()["link"]), "42")
        for url in ("https://evil.test/o/r/actions/runs/42", "https://github.com/other/r/actions/runs/42"):
            self.assertIsNone(pg.actions_run_id(ctx, url))

    def test_rerun_ledger_prevents_retries_even_after_ambiguous_error(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = SimpleNamespace(cache=Path(d), slug="o/r", host="github.com", selector="o/r")
            with patch.object(pg, "published_head"), patch.object(pg, "checks", return_value=[check("fail")]), \
                 patch.object(pg, "verify_run", return_value=dict(status="completed", run_attempt=1)), \
                 patch.object(pg, "gh", side_effect=pg.Stop("connection lost")) as gh:
                with self.assertRaisesRegex(pg.Stop, "connection lost"):
                    pg.rerun(ctx, "42", "head")
                with self.assertRaisesRegex(pg.Stop, "already attempted"):
                    pg.rerun(ctx, "42", "head")
                self.assertEqual(gh.call_count, 1)

    def test_resolve_requires_thread_membership(self):
        ctx = SimpleNamespace(graphql=Mock())
        with patch.object(pg, "published_head"), patch.object(pg, "threads", return_value=[{"id": "actual"}]):
            with self.assertRaises(pg.Stop):
                pg.resolve(ctx, "other-pr-thread", "head")
        ctx.graphql.assert_not_called()

    def test_matching_pr_disambiguates_forks(self):
        ctx = object.__new__(pg.Context)
        ctx.branch = "feature"
        ctx.push_repo = {"nameWithOwner": "o/r"}
        self.assertTrue(ctx.matches(pr()))
        self.assertFalse(ctx.matches(pr(headRepositoryOwner={"login": "someone-else"})))

    def test_existing_upsert_does_not_edit_unchanged_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            title, body = Path(d) / "title", Path(d) / "body"
            title.write_text("Fix thing\n")
            body.write_text("Evidence")
            ctx = SimpleNamespace(pr=pr(), view=Mock(return_value=pr()), selector="o/r")
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.upsert(ctx, upsert_args(title_file=str(title), body_file=str(body)))
                gh.assert_not_called()

    def test_new_pr_requires_metadata_before_push(self):
        with patch.object(pg, "sync") as sync:
            with self.assertRaises(pg.Stop):
                pg.upsert(SimpleNamespace(pr=None), upsert_args(title_file=None, body_file=None))
            sync.assert_not_called()

    def test_upsert_preserves_concurrent_metadata_edits(self):
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "body"
            body.write_text("New evidence")
            ctx = SimpleNamespace(pr=pr(), view=Mock(return_value=pr(body="Human update")), selector="o/r")
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh:
                with self.assertRaises(pg.Stop) as caught:
                    pg.upsert(ctx, upsert_args(body_file=str(body)))
            self.assertEqual(caught.exception.kind, "WAITING")
            gh.assert_not_called()

    def test_upsert_allows_concurrent_change_to_omitted_field(self):
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "body"
            body.write_text("New evidence")
            ctx = SimpleNamespace(pr=pr(), view=Mock(return_value=pr(title="Human title")), selector="o/r")
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.upsert(ctx, upsert_args(body_file=str(body)))
            gh.assert_called_once_with("pr", "edit", "7", "--repo", "o/r", "--body-file", str(body))

    def test_upsert_accepts_already_applied_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "body"
            body.write_text("New evidence")
            ctx = SimpleNamespace(pr=pr(), view=Mock(return_value=pr(body="New evidence")), selector="o/r")
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.upsert(ctx, upsert_args(body_file=str(body)))
            gh.assert_not_called()

    def test_keep_draft_does_not_mark_existing_pr_ready(self):
        ctx = SimpleNamespace(pr=pr(isDraft=True), view=Mock(return_value=pr(isDraft=True)))
        with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
            pg.upsert(ctx, upsert_args(keep_draft=True))
        gh.assert_not_called()

    def test_keep_draft_creates_draft_pr(self):
        with tempfile.TemporaryDirectory() as d:
            title, body = Path(d) / "title", Path(d) / "body"
            title.write_text("Fix thing")
            body.write_text("Evidence")
            ctx = SimpleNamespace(pr=None, repo={"url": "https://github.com/o/r"},
                                  push_repo={"url": "https://github.com/o/r"},
                                  branch="feature", base="main", selector="o/r",
                                  view=Mock(return_value=pr(isDraft=True)), find_pr=Mock(return_value=pr(isDraft=True)))
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.upsert(ctx, upsert_args(title_file=str(title), body_file=str(body), keep_draft=True))
            gh.assert_called_once_with("pr", "create", "--repo", "o/r", "--head", "feature", "--base", "main",
                                       "--title", "Fix thing", "--body-file", str(body), "--draft")

    def test_upsert_updates_only_changed_fields_and_marks_ready(self):
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "body"
            body.write_text("Evidence\n- [x] Verified `literal` $(text)\n")
            ctx = SimpleNamespace(pr=pr(), view=Mock(return_value=pr(isDraft=True)), selector="o/r")
            with patch.object(pg, "sync"), patch.object(pg, "gh") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.upsert(ctx, upsert_args(title_file=None, body_file=str(body)))
            self.assertEqual(gh.call_args_list[0].args,
                             ("pr", "edit", "7", "--repo", "o/r", "--body-file", str(body)))
            self.assertEqual(gh.call_args_list[1].args, ("pr", "ready", "7", "--repo", "o/r"))

    def test_new_fork_pr_creation_is_explicit_and_recovers_race(self):
        with tempfile.TemporaryDirectory() as d:
            title, body = Path(d) / "title", Path(d) / "body"
            title.write_text("Fix thing")
            body.write_text("Evidence")
            ctx = SimpleNamespace(pr=None, repo={"url": "https://github.com/o/r"},
                                  push_repo={"url": "https://github.com/fork/r", "nameWithOwner": "fork/r"},
                                  branch="feature", base="release", selector="o/r", view=Mock(return_value=pr()),
                                  find_pr=Mock(return_value=pr()))
            with patch.object(pg, "sync"), patch.object(pg, "gh", side_effect=pg.Stop("already exists")) as gh, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pg.upsert(ctx, upsert_args(title_file=str(title), body_file=str(body))), 0)
            self.assertIn("fork:feature", gh.call_args.args)
            self.assertIn("release", gh.call_args.args)
            self.assertEqual(gh.call_count, 1)

    def test_published_head_guard_rejects_unpushed_fix_before_resolve(self):
        ctx = SimpleNamespace(view=Mock(return_value=pr()), remote="origin", branch="feature")
        with patch.object(pg, "clean"), patch.object(pg, "git", side_effect=["feature", "head refs/heads/feature", "local-fix"]):
            with self.assertRaises(pg.Stop) as caught:
                pg.published_head(ctx, "head")
        self.assertEqual(caught.exception.kind, "WAITING")

    def test_ambiguous_open_prs_and_wrong_base_fail_closed(self):
        ctx = object.__new__(pg.Context)
        ctx.branch, ctx.selector, ctx.push_repo = "feature", "o/r", {"nameWithOwner": "o/r"}
        ctx.base_override = None
        with patch.object(pg, "gh_json", return_value=[pr(), pr(number=8, baseRefName="release")]):
            with self.assertRaisesRegex(pg.Stop, "Multiple"):
                ctx.find_pr()
            ctx.base_override = "release"
            self.assertEqual(ctx.find_pr()["number"], 8)
            ctx.base_override = "missing"
            with self.assertRaisesRegex(pg.Stop, "retarget"):
                ctx.find_pr()

    def test_wait_returns_on_failure_without_busy_polling(self):
        ctx = SimpleNamespace(pr=pr())
        facts = {"pr": pr()["url"]}
        with patch.object(pg, "snapshot", side_effect=[("WAITING", facts), ("ACTION", facts)]) as snap, \
             patch.object(pg.time, "sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pg.status(ctx, 45), 2)
        self.assertEqual(snap.call_count, 2)
        sleep.assert_called_once()

    def test_overlapping_mutations_fail_and_lock_is_released(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = SimpleNamespace(cache=Path(d))
            with pg.mutation_lock(ctx):
                with self.assertRaises(pg.Stop):
                    with pg.mutation_lock(ctx):
                        self.fail("overlapping writer entered")
            self.assertFalse((Path(d) / "mutation.lock").exists())

    def test_log_cache_uses_attempt_and_does_not_download_twice(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = SimpleNamespace(cache=Path(d), slug="o/r", host="github.com", selector="o/r", view=Mock(return_value=pr()))
            info = dict(status="completed", run_attempt=1)
            with patch.object(pg, "checks", return_value=[check("fail")]), patch.object(pg, "verify_run", return_value=info), \
                 patch.object(pg, "gh", return_value="FAIL meaningful error") as gh, contextlib.redirect_stdout(io.StringIO()):
                pg.logs(ctx, 4)
                pg.logs(ctx, 4)
                self.assertEqual(gh.call_count, 1)
                info["run_attempt"] = 2
                pg.logs(ctx, 4)
                self.assertEqual(gh.call_count, 2)


class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = Path.cwd()
        self.addCleanup(os.chdir, self.old)
        self.folder = Path(self.tmp.name)
        self.bare = self.folder / "remote.git"
        self.work = self.folder / "work"
        self.other = self.folder / "other"
        pg.git("init", "--bare", str(self.bare))
        pg.git("init", "-b", "main", str(self.work))
        os.chdir(self.work)
        self.identity()
        self.commit("seed", "seed\n")
        pg.git("remote", "add", "origin", str(self.bare))
        pg.git("push", "-u", "origin", "main")
        pg.git("symbolic-ref", "HEAD", "refs/heads/main")
        pg.git("checkout", "-b", "feature")
        self.commit("feature", "feature\n")
        pg.git("push", "-u", "origin", "feature")
        pg.git("clone", "--branch", "main", str(self.bare), str(self.other))
        os.chdir(self.other)
        self.identity()
        os.chdir(self.work)
        self.ctx = object.__new__(pg.Context)
        self.ctx.pr = None
        self.ctx.remote = "origin"
        self.ctx.branch = "feature"
        self.ctx.base = "main"
        self.ctx.repo = {"url": str(self.bare)}
        self.ctx.push_repo = self.ctx.repo
        self.ctx.base_ref = "refs/pr-green/test/base"
        self.ctx.head_ref = "refs/pr-green/test/head"

    def identity(self):
        pg.git("config", "user.name", "Test")
        pg.git("config", "user.email", "test@example.invalid")
        pg.git("config", "commit.gpgsign", "false")

    def commit(self, name, contents):
        Path(name).write_text(contents)
        pg.git("add", "--", name)
        pg.git("commit", "-m", name)
        return pg.git("rev-parse", "HEAD")

    def test_integrates_base_and_collaborator_preserving_both(self):
        original = pg.git("rev-parse", "HEAD")
        os.chdir(self.other)
        base = self.commit("base-change", "base change")
        pg.git("push", "origin", "main")
        pg.git("checkout", "feature")
        colleague = self.commit("colleague", "colleague change")
        pg.git("push", "origin", "feature")
        os.chdir(self.work)
        self.commit("local", "local change")
        head = pg.sync(self.ctx)
        for tip in (original, base, colleague):
            self.assertTrue(pg.ancestor(tip, head))
        self.assertEqual(pg.git("ls-remote", "origin", "refs/heads/feature").split()[0], head)
        self.assertEqual(pg.sync(self.ctx), head)  # no extra commit/push needed

    def test_dirty_changes_are_preserved_without_push(self):
        Path("user-file").write_text("keep me")
        before = pg.git("ls-remote", "origin", "refs/heads/feature")
        with self.assertRaisesRegex(pg.Stop, "uncommitted"):
            pg.sync(self.ctx)
        self.assertEqual(Path("user-file").read_text(), "keep me")
        self.assertEqual(pg.git("ls-remote", "origin", "refs/heads/feature"), before)

    def test_branch_switch_during_fetch_does_not_merge_or_push(self):
        original = self.ctx.fetch
        before = pg.git("ls-remote", "origin", "refs/heads/feature")
        main = pg.git("rev-parse", "main")
        def fetch_then_switch():
            result = original()
            pg.git("checkout", "main")
            return result
        self.ctx.fetch = fetch_then_switch
        with self.assertRaisesRegex(pg.Stop, "Local branch changed"):
            pg.sync(self.ctx)
        self.assertEqual(pg.git("rev-parse", "main"), main)
        self.assertEqual(pg.git("ls-remote", "origin", "refs/heads/feature"), before)

    def test_published_head_rejects_other_branch_at_same_commit(self):
        head = pg.git("rev-parse", "HEAD")
        self.ctx.view = Mock(return_value=pr(headRefOid=head))
        pg.git("checkout", "-b", "other-branch")
        with self.assertRaisesRegex(pg.Stop, "Local branch changed"):
            pg.published_head(self.ctx, head)

    def test_conflict_keeps_remote_unchanged_and_exposes_action(self):
        self.commit("seed", "feature version\n")
        os.chdir(self.other)
        self.commit("seed", "base version\n")
        pg.git("push", "origin", "main")
        os.chdir(self.work)
        before = pg.git("ls-remote", "origin", "refs/heads/feature")
        with self.assertRaises(pg.Stop) as caught:
            pg.sync(self.ctx)
        self.assertEqual(caught.exception.kind, "ACTION")
        self.assertIn("UU seed", pg.git("status", "--porcelain"))
        self.assertEqual(pg.git("ls-remote", "origin", "refs/heads/feature"), before)

    def test_push_race_does_not_force_overwrite(self):
        original = self.ctx.fetch
        def fetch_then_race():
            result = original()
            os.chdir(self.other)
            pg.git("checkout", "feature")
            self.commit("racing", "concurrent change")
            pg.git("push", "origin", "feature")
            os.chdir(self.work)
            return result
        self.ctx.fetch = fetch_then_race
        self.commit("local", "local change")
        with self.assertRaises(pg.Stop):
            pg.sync(self.ctx)
        os.chdir(self.other)
        self.assertEqual(pg.git("ls-remote", "origin", "refs/heads/feature").split()[0], pg.git("rev-parse", "HEAD"))


class InstallTests(unittest.TestCase):
    def test_installer_preserves_old_install_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            dest = home / ".agents/skills/pr-green"
            dest.mkdir(parents=True)
            (dest / "old-marker").write_text("preserve")
            shim = home / ".cursor/commands/pr-green.md"
            shim.parent.mkdir(parents=True)
            shim.write_text("old command")
            command = ["python3", str(SCRIPT.parent / "install.py"), "--home", d]
            for _ in range(2):
                subprocess.run(command, check=True, capture_output=True)
            self.assertTrue((home / ".codex/skills/pr-green/SKILL.md").is_file())
            self.assertTrue((home / ".local/bin/pr-green").is_file())
            self.assertEqual(len(list((home / ".agents/skill-backups").glob("pr-green.backup-*/old-marker"))), 1)
            self.assertIn(str(dest / "SKILL.md"), shim.read_text())
            self.assertEqual(len(list(shim.parent.glob("pr-green.md.backup-*"))), 1)


if __name__ == "__main__":
    unittest.main()

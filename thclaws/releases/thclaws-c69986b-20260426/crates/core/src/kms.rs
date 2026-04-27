//! Knowledge Management System (KMS) — Karpathy-style LLM wikis.
//!
//! A KMS is a directory of markdown pages plus an `index.md` table of
//! contents and a `log.md` change history. Two scopes:
//!
//! - **User**: `~/.config/thclaws/kms/<name>/`
//! - **Project**: `.thclaws/kms/<name>/`
//!
//! Users mark any subset of KMS as "active" in `.thclaws/settings.json`'s
//! `kms.active` array. When a chat turn runs, each active KMS's
//! `index.md` is concatenated into the system prompt, and the
//! `KmsRead` / `KmsSearch` tools let the model pull in specific pages
//! on demand. No embeddings, no vector store — just grep + read, per
//! Karpathy's pattern.
//!
//! Layout of a KMS directory:
//!
//! ```text
//! <kms_root>/
//!   index.md     — table of contents, one line per page (model reads this)
//!   log.md       — append-only change log (human and model write here)
//!   SCHEMA.md    — optional: shape rules for pages (not enforced in code)
//!   pages/       — individual wiki pages, one per topic
//!   sources/     — raw source material (URLs, PDFs, notes) — optional
//! ```

use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum KmsScope {
    User,
    Project,
}

impl KmsScope {
    pub fn as_str(self) -> &'static str {
        match self {
            KmsScope::User => "user",
            KmsScope::Project => "project",
        }
    }
}

/// A KMS instance — its scope, name, and root directory.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KmsRef {
    pub name: String,
    pub scope: KmsScope,
    pub root: PathBuf,
}

impl KmsRef {
    pub fn index_path(&self) -> PathBuf {
        self.root.join("index.md")
    }

    pub fn log_path(&self) -> PathBuf {
        self.root.join("log.md")
    }

    pub fn pages_dir(&self) -> PathBuf {
        self.root.join("pages")
    }

    pub fn schema_path(&self) -> PathBuf {
        self.root.join("SCHEMA.md")
    }

    /// Read `index.md`. Returns `""` (not an error) when the file is absent,
    /// OR when the path is a symlink (refused to prevent a cloned KMS
    /// with `index.md -> /etc/passwd` from exfiltrating through the
    /// system prompt). A fresh KMS with no entries yet is a valid state.
    pub fn read_index(&self) -> String {
        let path = self.index_path();
        if let Ok(md) = std::fs::symlink_metadata(&path) {
            if md.file_type().is_symlink() {
                return String::new();
            }
        }
        std::fs::read_to_string(&path).unwrap_or_default()
    }

    /// Resolve a page name to a file path inside `pages/`. `.md` is added
    /// if missing. Returns an error if the resolved path escapes the KMS
    /// directory via `..`, an absolute path, path separators, null bytes,
    /// or symlink trickery (e.g. `pages/` itself symlinked outside, or a
    /// page file symlinked to `/etc/passwd`).
    pub fn page_path(&self, page: &str) -> Result<PathBuf> {
        // Reject obviously-bad names before touching the filesystem.
        if page.is_empty()
            || page.contains("..")
            || page.contains('/')
            || page.contains('\\')
            || page.contains('\0')
            || page.chars().any(|c| c.is_control())
            || Path::new(page).is_absolute()
        {
            return Err(Error::Tool(format!(
                "invalid page name '{page}' — no '..', path separators, or control chars"
            )));
        }
        let name = if page.ends_with(".md") {
            page.to_string()
        } else {
            format!("{page}.md")
        };
        let candidate = self.pages_dir().join(&name);

        // Canonicalize the scope root and require the candidate to resolve
        // *within* this specific KMS directory under it. This defeats
        // symlink bypasses: if `pages/` or the page file itself is a
        // symlink pointing outside, the canonical candidate escapes the
        // KMS root and we reject.
        let canon_candidate = std::fs::canonicalize(&candidate).map_err(|e| {
            Error::Tool(format!(
                "cannot resolve page path '{}': {e}",
                candidate.display()
            ))
        })?;
        let canon_scope = scope_root(self.scope)
            .and_then(|p| std::fs::canonicalize(&p).ok())
            .ok_or_else(|| Error::Tool("kms scope root not resolvable".into()))?;
        let canon_kms_root = canon_scope.join(&self.name);
        if !canon_candidate.starts_with(&canon_kms_root) {
            return Err(Error::Tool(format!(
                "page '{page}' resolves outside the KMS directory — symlink escape rejected"
            )));
        }
        // Also require it's a regular file, not a directory.
        let meta = std::fs::metadata(&canon_candidate)
            .map_err(|e| Error::Tool(format!("cannot stat page '{page}': {e}")))?;
        if !meta.is_file() {
            return Err(Error::Tool(format!("page '{page}' is not a regular file")));
        }
        Ok(candidate)
    }
}

fn user_root() -> Option<PathBuf> {
    crate::util::home_dir().map(|h| h.join(".config/thclaws/kms"))
}

fn project_root() -> PathBuf {
    std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join(".thclaws/kms")
}

fn scope_root(scope: KmsScope) -> Option<PathBuf> {
    match scope {
        KmsScope::User => user_root(),
        KmsScope::Project => Some(project_root()),
    }
}

/// Enumerate KMS directories under one scope. Silently ignores missing
/// roots — fresh installs have neither. Symlinks are intentionally
/// skipped: a user can't turn a KMS directory into a symlink to `/etc`
/// and have thClaws enumerate it.
fn list_in(scope: KmsScope) -> Vec<KmsRef> {
    let Some(root) = scope_root(scope) else {
        return Vec::new();
    };
    let Ok(entries) = std::fs::read_dir(&root) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for entry in entries.flatten() {
        // symlink_metadata → file_type doesn't follow the symlink, so
        // a `ln -s /etc foo` sitting in the kms dir returns is_symlink.
        let ft = match entry.file_type() {
            Ok(ft) => ft,
            Err(_) => continue,
        };
        if ft.is_symlink() || !ft.is_dir() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        if name.starts_with('.') {
            continue;
        }
        out.push(KmsRef {
            name,
            scope,
            root: entry.path(),
        });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    out
}

/// List every KMS visible to this process — project entries first, then
/// user. If the same name exists in both scopes, both are returned;
/// callers that need to pick one treat project as higher priority.
pub fn list_all() -> Vec<KmsRef> {
    let mut out = list_in(KmsScope::Project);
    out.extend(list_in(KmsScope::User));
    out
}

/// Find a KMS by name. Project scope wins over user on collision — this
/// matches how project instructions override user instructions elsewhere
/// in thClaws. Returns `None` when no KMS by that name exists, or when
/// the matching directory is a symlink (symlinks are rejected to prevent
/// `ln -s /etc <kms-name>` style exfiltration).
pub fn resolve(name: &str) -> Option<KmsRef> {
    for scope in [KmsScope::Project, KmsScope::User] {
        if let Some(root) = scope_root(scope) {
            let candidate = root.join(name);
            // symlink_metadata doesn't follow the symlink.
            let Ok(meta) = std::fs::symlink_metadata(&candidate) else {
                continue;
            };
            if meta.is_symlink() || !meta.is_dir() {
                continue;
            }
            return Some(KmsRef {
                name: name.to_string(),
                scope,
                root: candidate,
            });
        }
    }
    None
}

/// Create a new KMS. Seeds `index.md`, `log.md`, and `SCHEMA.md` with
/// minimal starter content so the model has something to read on day
/// one. No-op and returns `Ok(existing)` if a KMS by that name already
/// exists at the requested scope.
pub fn create(name: &str, scope: KmsScope) -> Result<KmsRef> {
    if name.is_empty() {
        return Err(Error::Config("kms name must not be empty".into()));
    }
    if name.contains('/')
        || name.contains('\\')
        || name.contains("..")
        || name.contains('\0')
        || name.chars().any(|c| c.is_control())
        || name.starts_with('.')
        || Path::new(name).is_absolute()
    {
        return Err(Error::Config(format!(
            "invalid kms name '{name}' — no path separators, '..', control chars, or leading '.'"
        )));
    }
    let root = scope_root(scope)
        .ok_or_else(|| Error::Config("cannot locate user home directory".into()))?
        .join(name);
    if root.is_dir() {
        return Ok(KmsRef {
            name: name.to_string(),
            scope,
            root,
        });
    }
    std::fs::create_dir_all(root.join("pages"))?;
    std::fs::create_dir_all(root.join("sources"))?;
    let kref = KmsRef {
        name: name.to_string(),
        scope,
        root,
    };
    std::fs::write(
        kref.index_path(),
        format!("# {name}\n\nKnowledge base index — list each page with a one-line summary.\n"),
    )?;
    std::fs::write(
        kref.log_path(),
        "# Change log\n\nAppend-only list of ingests / edits / lints.\n",
    )?;
    std::fs::write(
        kref.schema_path(),
        "# Schema\n\nDescribe the shape of pages in this KMS — required\n\
         sections, naming conventions, cross-link style. Both you and the\n\
         agent read this before editing pages.\n",
    )?;
    Ok(kref)
}

/// Extensions a user can ingest into a KMS. Deliberately narrow: these
/// are the text formats `KmsRead` can hand to the model meaningfully,
/// and that a human would expect to grep with `KmsSearch`. Binary
/// formats (PDF, images, archives) are rejected with a hint to convert
/// them to markdown first — we'd rather make the user choose the
/// conversion than silently store a blob the model can't read.
pub const INGEST_EXTENSIONS: &[&str] = &["md", "markdown", "txt", "rst", "log", "json"];

/// Reserved aliases that collide with the KMS starter files — refuse
/// to ingest into them, otherwise a `/kms ingest notes README.md as index`
/// would clobber the index with no way back except `--force`.
const RESERVED_PAGE_STEMS: &[&str] = &["index", "log", "SCHEMA"];

/// What `ingest()` did. `overwrote == true` means `--force` replaced an
/// existing page; the handler surfaces that to the user so a typo in
/// the alias doesn't silently nuke a page.
#[derive(Debug)]
pub struct IngestResult {
    pub alias: String,
    pub target: PathBuf,
    pub summary: String,
    pub overwrote: bool,
}

/// Copy `source` into `kms.pages/<alias>.<ext>`, append an entry to
/// `index.md`, and log the ingest. Fails if the target page already
/// exists unless `force` is true; also fails on extensions outside
/// `INGEST_EXTENSIONS`. `alias` defaults to the sanitised file stem.
/// Writes are best-effort in order (copy → index → log); if any step
/// partially succeeds we still return the error so the caller can tell
/// the user something went wrong.
pub fn ingest(
    kms: &KmsRef,
    source: &Path,
    alias: Option<&str>,
    force: bool,
) -> Result<IngestResult> {
    let meta = std::fs::metadata(source)
        .map_err(|e| Error::Tool(format!("cannot stat source '{}': {e}", source.display())))?;
    if !meta.is_file() {
        return Err(Error::Tool(format!(
            "source '{}' is not a regular file",
            source.display()
        )));
    }

    let ext_raw = source.extension().and_then(|e| e.to_str()).ok_or_else(|| {
        Error::Tool(format!(
            "'{}' has no extension — ingest requires one of: {}",
            source.display(),
            INGEST_EXTENSIONS.join(", "),
        ))
    })?;
    let ext = ext_raw.to_ascii_lowercase();
    if !INGEST_EXTENSIONS.iter().any(|e| *e == ext) {
        return Err(Error::Tool(format!(
            "extension '.{ext}' not supported — allowed: {}",
            INGEST_EXTENSIONS.join(", "),
        )));
    }

    let raw_alias = match alias {
        Some(a) => a.to_string(),
        None => source
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("page")
            .to_string(),
    };
    let alias = sanitize_alias(&raw_alias);
    if alias.is_empty() {
        return Err(Error::Tool(format!(
            "alias '{raw_alias}' sanitises to empty — use [A-Za-z0-9_-] characters"
        )));
    }
    if RESERVED_PAGE_STEMS
        .iter()
        .any(|r| r.eq_ignore_ascii_case(&alias))
    {
        return Err(Error::Tool(format!(
            "alias '{alias}' is reserved — pick another"
        )));
    }

    let target = kms.pages_dir().join(format!("{alias}.{ext}"));
    let overwrote = target.exists();
    if overwrote && !force {
        return Err(Error::Tool(format!(
            "page '{alias}.{ext}' already exists — re-run with --force to overwrite"
        )));
    }

    std::fs::copy(source, &target).map_err(|e| {
        Error::Tool(format!(
            "copy {} → {} failed: {e}",
            source.display(),
            target.display()
        ))
    })?;

    let summary = first_summary_line(&target);
    append_index_entry(kms, &alias, &ext, &summary, overwrote)?;
    append_log_entry(kms, source, &alias, &ext, overwrote)?;

    Ok(IngestResult {
        alias,
        target,
        summary,
        overwrote,
    })
}

/// Keep only `[A-Za-z0-9_-]`; collapse anything else to `_`. An empty
/// result returns empty so the caller can reject it with a useful
/// message rather than writing a page named "".
fn sanitize_alias(raw: &str) -> String {
    let cleaned: String = raw
        .trim()
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect();
    cleaned.trim_matches('_').to_string()
}

/// First non-empty line of the just-copied file, trimmed to 80 chars.
/// Leading markdown `#` / `-` / `*` / `>` markers are stripped so the
/// summary reads as a snippet, not as heading syntax inside the index
/// bullet. Returns "(empty)" for empty files.
fn first_summary_line(target: &Path) -> String {
    let text = match std::fs::read_to_string(target) {
        Ok(t) => t,
        Err(_) => return "(binary or unreadable)".into(),
    };
    for line in text.lines() {
        let stripped = line.trim_start_matches(|c: char| {
            c == '#' || c == '-' || c == '*' || c == '>' || c.is_whitespace()
        });
        let trimmed = stripped.trim();
        if !trimmed.is_empty() {
            let mut s: String = trimmed.chars().take(80).collect();
            if trimmed.chars().count() > 80 {
                s.push('…');
            }
            return s;
        }
    }
    "(empty)".into()
}

fn append_index_entry(
    kms: &KmsRef,
    alias: &str,
    ext: &str,
    summary: &str,
    overwrote: bool,
) -> Result<()> {
    use std::io::Write;
    let path = kms.index_path();
    let mut existing = std::fs::read_to_string(&path).unwrap_or_default();
    let line = format!("- [{alias}](pages/{alias}.{ext}) — {summary}\n");
    if overwrote {
        // Best-effort: if an entry for this alias already exists, drop
        // it so the re-ingest doesn't produce a duplicate bullet. Match
        // is anchored to `(pages/<alias>.<ext>)` so we don't cross-hit
        // unrelated aliases that happen to share a prefix.
        let needle = format!("(pages/{alias}.{ext})");
        existing = existing
            .lines()
            .filter(|l| !l.contains(&needle))
            .collect::<Vec<_>>()
            .join("\n");
        if !existing.ends_with('\n') {
            existing.push('\n');
        }
    }
    if !existing.ends_with('\n') && !existing.is_empty() {
        existing.push('\n');
    }
    existing.push_str(&line);
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(&path)
        .map_err(|e| Error::Tool(format!("open {}: {e}", path.display())))?;
    f.write_all(existing.as_bytes())
        .map_err(|e| Error::Tool(format!("write {}: {e}", path.display())))?;
    Ok(())
}

fn append_log_entry(
    kms: &KmsRef,
    source: &Path,
    alias: &str,
    ext: &str,
    overwrote: bool,
) -> Result<()> {
    use std::io::Write;
    let path = kms.log_path();
    let verb = if overwrote { "re-ingested" } else { "ingested" };
    let line = format!(
        "- {date} {verb} `{src}` → `pages/{alias}.{ext}`\n",
        date = crate::usage::today_str(),
        src = source.display(),
    );
    let mut f = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(&path)
        .map_err(|e| Error::Tool(format!("open {}: {e}", path.display())))?;
    f.write_all(line.as_bytes())
        .map_err(|e| Error::Tool(format!("write {}: {e}", path.display())))?;
    Ok(())
}

/// Render the concatenated active-KMS block to splice into a system
/// prompt. One section per KMS, heading is its name. Empty string when
/// no active KMS or when active names resolve to nothing.
pub fn system_prompt_section(active: &[String]) -> String {
    let mut parts = Vec::new();
    for name in active {
        let Some(kref) = resolve(name) else { continue };
        let index = kref.read_index();
        let body = if index.trim().is_empty() {
            "(empty index)".to_string()
        } else {
            index.trim().to_string()
        };
        parts.push(format!(
            "## KMS: {name} ({scope})\n\n{body}\n\n\
             To read a specific page, call `KmsRead(kms: \"{name}\", page: \"<page>\")`.\n\
             To grep all pages, call `KmsSearch(kms: \"{name}\", pattern: \"...\")`.",
            scope = kref.scope.as_str()
        ));
    }
    if parts.is_empty() {
        String::new()
    } else {
        format!(
            "# Active knowledge bases\n\n\
             The following KMS are attached to this conversation. Their indices are below \
             — consult them before answering when the user's question overlaps. Treat KMS \
             content as authoritative over your training data for the topics it covers.\n\n{}",
            parts.join("\n\n")
        )
    }
}

/// Test-only lock shared by every test in this module *and* in
/// `tools::kms` that mutates the process env (HOME, cwd). Without
/// this, parallel tests race on env — which can also break unrelated
/// tests (bash/grep) whose sandbox resolver reads cwd.
#[cfg(test)]
pub(crate) fn test_env_lock() -> std::sync::MutexGuard<'static, ()> {
    use std::sync::{Mutex, OnceLock};
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|e| e.into_inner())
}

#[cfg(test)]
mod tests {
    use super::*;

    struct EnvGuard {
        _lock: std::sync::MutexGuard<'static, ()>,
        prev_home: Option<String>,
        prev_userprofile: Option<String>,
        prev_cwd: std::path::PathBuf,
        _home_dir: tempfile::TempDir,
    }

    impl Drop for EnvGuard {
        fn drop(&mut self) {
            // Restore cwd first — set_current_dir against a dropped
            // tempdir would fail silently otherwise.
            let _ = std::env::set_current_dir(&self.prev_cwd);
            match &self.prev_home {
                Some(h) => std::env::set_var("HOME", h),
                None => std::env::remove_var("HOME"),
            }
            match &self.prev_userprofile {
                Some(h) => std::env::set_var("USERPROFILE", h),
                None => std::env::remove_var("USERPROFILE"),
            }
        }
    }

    /// Acquire exclusive access to the process env + cwd for this
    /// test, set HOME (+ USERPROFILE on Windows) to a fresh tempdir,
    /// leave cwd pointing at that tempdir. Dropped at end of test to
    /// restore.
    fn scoped_home() -> EnvGuard {
        let lock = test_env_lock();
        let prev_home = std::env::var("HOME").ok();
        let prev_userprofile = std::env::var("USERPROFILE").ok();
        let prev_cwd = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
        let dir = tempfile::tempdir().unwrap();
        std::env::set_var("HOME", dir.path());
        std::env::set_var("USERPROFILE", dir.path());
        std::env::set_current_dir(dir.path()).unwrap();
        EnvGuard {
            _lock: lock,
            prev_home,
            prev_userprofile,
            prev_cwd,
            _home_dir: dir,
        }
    }

    #[test]
    fn create_seeds_starter_files() {
        let _home = scoped_home();
        let k = create("notes", KmsScope::User).unwrap();
        assert!(k.index_path().exists());
        assert!(k.log_path().exists());
        assert!(k.schema_path().exists());
        assert!(k.pages_dir().is_dir());
    }

    #[test]
    fn create_is_idempotent() {
        let _home = scoped_home();
        let a = create("notes", KmsScope::User).unwrap();
        let b = create("notes", KmsScope::User).unwrap();
        assert_eq!(a.root, b.root);
    }

    #[test]
    fn create_rejects_path_traversal() {
        let _home = scoped_home();
        assert!(create("../evil", KmsScope::User).is_err());
        assert!(create("foo/bar", KmsScope::User).is_err());
    }

    #[test]
    fn resolve_prefers_project_over_user() {
        let _home = scoped_home();
        create("shared", KmsScope::User).unwrap();
        create("shared", KmsScope::Project).unwrap();
        let found = resolve("shared").unwrap();
        assert_eq!(found.scope, KmsScope::Project);
    }

    #[test]
    fn list_all_returns_project_then_user() {
        let _home = scoped_home();
        create("user-only", KmsScope::User).unwrap();
        create("proj-only", KmsScope::Project).unwrap();
        let all = list_all();
        assert_eq!(all.len(), 2);
        assert_eq!(all[0].scope, KmsScope::Project);
        assert_eq!(all[1].scope, KmsScope::User);
    }

    #[test]
    fn system_prompt_section_empty_when_no_active() {
        let _home = scoped_home();
        assert_eq!(system_prompt_section(&[]), "");
    }

    #[test]
    fn system_prompt_section_includes_index_text() {
        let _home = scoped_home();
        let k = create("nb", KmsScope::User).unwrap();
        std::fs::write(k.index_path(), "# nb\n- [foo](pages/foo.md) — foo page\n").unwrap();
        let out = system_prompt_section(&["nb".into()]);
        assert!(out.contains("## KMS: nb"));
        assert!(out.contains("foo page"));
        assert!(out.contains("KmsRead"));
    }

    #[test]
    fn system_prompt_section_skips_missing() {
        let _home = scoped_home();
        let out = system_prompt_section(&["does-not-exist".into()]);
        assert_eq!(out, "");
    }

    #[test]
    fn page_path_rejects_traversal() {
        let _home = scoped_home();
        let k = create("nb", KmsScope::User).unwrap();
        assert!(k.page_path("../../etc/passwd").is_err());
        assert!(k.page_path("/etc/passwd").is_err());
        assert!(k.page_path("foo/bar").is_err()); // path separator
        assert!(k.page_path("").is_err()); // empty name
        assert!(k.page_path("foo\0bar").is_err()); // null byte

        // The happy path: create the file first (page_path now requires
        // the file to exist so it can canonicalize + symlink-check).
        std::fs::write(k.pages_dir().join("ok-page.md"), "body").unwrap();
        assert!(k.page_path("ok-page").is_ok());
    }

    #[cfg(unix)]
    #[test]
    fn page_path_rejects_symlink_to_outside() {
        use std::os::unix::fs::symlink;
        let _home = scoped_home();
        let k = create("nb", KmsScope::User).unwrap();

        // Attacker plants a symlink in pages/ to an outside target.
        let target_dir = tempfile::tempdir().unwrap();
        let outside_file = target_dir.path().join("secret.md");
        std::fs::write(&outside_file, "top secret").unwrap();
        let symlink_path = k.pages_dir().join("leaked.md");
        symlink(&outside_file, &symlink_path).unwrap();

        // Despite the file existing (via symlink), page_path rejects
        // because canonical candidate escapes the KMS root.
        let result = k.page_path("leaked");
        assert!(result.is_err(), "expected symlink to be rejected");
        let err_str = format!("{}", result.unwrap_err());
        assert!(
            err_str.contains("symlink escape") || err_str.contains("outside the KMS"),
            "unexpected error: {err_str}"
        );
    }

    #[test]
    fn ingest_copies_file_and_updates_index() {
        let _home = scoped_home();
        let k = create("notes", KmsScope::Project).unwrap();
        let src_dir = tempfile::tempdir().unwrap();
        let src = src_dir.path().join("intro.md");
        std::fs::write(&src, "# Intro\n\nFirst real line of content.\n").unwrap();

        let result = ingest(&k, &src, None, false).unwrap();
        assert_eq!(result.alias, "intro");
        assert!(!result.overwrote);
        assert!(result.target.exists());

        // Body was copied verbatim.
        let body = std::fs::read_to_string(&result.target).unwrap();
        assert!(body.contains("First real line"));

        // Index.md now has a bullet pointing at the new page.
        let index = std::fs::read_to_string(k.index_path()).unwrap();
        assert!(
            index.contains("- [intro](pages/intro.md) — Intro"),
            "index missing bullet, got:\n{index}"
        );

        // Log.md gained a line referencing the source.
        let log = std::fs::read_to_string(k.log_path()).unwrap();
        assert!(log.contains("ingested"));
        assert!(log.contains("pages/intro.md"));
    }

    #[test]
    fn ingest_collides_without_force() {
        let _home = scoped_home();
        let k = create("notes", KmsScope::Project).unwrap();
        let src_dir = tempfile::tempdir().unwrap();
        let src = src_dir.path().join("page.md");
        std::fs::write(&src, "a").unwrap();

        ingest(&k, &src, Some("topic"), false).unwrap();
        let err = ingest(&k, &src, Some("topic"), false).unwrap_err();
        let msg = format!("{err}");
        assert!(
            msg.contains("already exists"),
            "expected collision, got: {msg}"
        );

        // --force replaces, and is flagged as overwrote.
        std::fs::write(&src, "b").unwrap();
        let r = ingest(&k, &src, Some("topic"), true).unwrap();
        assert!(r.overwrote);
        let body = std::fs::read_to_string(&r.target).unwrap();
        assert_eq!(body, "b");
    }

    #[test]
    fn ingest_rejects_unknown_extension() {
        let _home = scoped_home();
        let k = create("notes", KmsScope::Project).unwrap();
        let src_dir = tempfile::tempdir().unwrap();
        let src = src_dir.path().join("bin.xyz");
        std::fs::write(&src, "data").unwrap();
        let err = ingest(&k, &src, None, false).unwrap_err();
        assert!(format!("{err}").contains("not supported"));
    }

    #[test]
    fn ingest_rejects_reserved_alias() {
        let _home = scoped_home();
        let k = create("notes", KmsScope::Project).unwrap();
        let src_dir = tempfile::tempdir().unwrap();
        let src = src_dir.path().join("file.md");
        std::fs::write(&src, "x").unwrap();
        let err = ingest(&k, &src, Some("index"), false).unwrap_err();
        assert!(format!("{err}").contains("reserved"));
    }

    #[cfg(unix)]
    #[test]
    fn resolve_rejects_symlink_kms_dir() {
        use std::os::unix::fs::symlink;
        let _home = scoped_home();

        // Attacker plants a symlink where a KMS dir should be.
        let target = tempfile::tempdir().unwrap();
        let kms_root = scope_root(KmsScope::User).unwrap();
        std::fs::create_dir_all(&kms_root).unwrap();
        symlink(target.path(), kms_root.join("evil")).unwrap();

        // resolve() should not return a KmsRef for a symlinked dir.
        assert!(
            resolve("evil").is_none(),
            "symlinked KMS dir should be rejected"
        );
    }
}

//! Capture build-time metadata so released binaries can identify themselves.
//!
//! Sets the following `cargo:rustc-env` variables which `src/version.rs`
//! reads via `env!()`:
//!   THCLAWS_GIT_SHA       — short commit hash of HEAD, or "unknown"
//!   THCLAWS_GIT_DIRTY     — "1" if the working tree had uncommitted changes
//!                           at build time, "0" otherwise
//!   THCLAWS_GIT_BRANCH    — current branch name, or "unknown"
//!   THCLAWS_BUILD_TIME    — ISO-8601 UTC timestamp of the build
//!   THCLAWS_BUILD_PROFILE — "debug" / "release"
//!
//! The build script intentionally doesn't fail if git is missing (source
//! tarball installs, Docker without git, etc.) — it just reports "unknown".

use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    // Re-run when git HEAD moves (covers most branch switches and commits).
    println!("cargo:rerun-if-changed=../../../.git/HEAD");
    println!("cargo:rerun-if-changed=../../../.git/index");
    // Always re-run when build.rs itself changes.
    println!("cargo:rerun-if-changed=build.rs");

    let sha = git(&["rev-parse", "--short", "HEAD"]).unwrap_or_else(|| "unknown".into());
    let branch = git(&["rev-parse", "--abbrev-ref", "HEAD"]).unwrap_or_else(|| "unknown".into());
    let dirty = match git(&["status", "--porcelain"]) {
        Some(s) if !s.trim().is_empty() => "1",
        Some(_) => "0",
        None => "0",
    };

    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "unknown".into());
    let build_time = iso8601_utc_now();

    println!("cargo:rustc-env=THCLAWS_GIT_SHA={sha}");
    println!("cargo:rustc-env=THCLAWS_GIT_BRANCH={branch}");
    println!("cargo:rustc-env=THCLAWS_GIT_DIRTY={dirty}");
    println!("cargo:rustc-env=THCLAWS_BUILD_TIME={build_time}");
    println!("cargo:rustc-env=THCLAWS_BUILD_PROFILE={profile}");
}

fn git(args: &[&str]) -> Option<String> {
    let out = Command::new("git").args(args).output().ok()?;
    if !out.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
}

/// Render a best-effort ISO-8601 UTC timestamp without pulling in `chrono`.
/// Good enough for human-readable build metadata; don't parse it.
fn iso8601_utc_now() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Days since 1970-01-01 → civil date (Howard Hinnant's algorithm).
    let days = (secs / 86_400) as i64;
    let (y, m, d) = civil_from_days(days);
    let rem = secs % 86_400;
    let h = rem / 3600;
    let mi = (rem % 3600) / 60;
    let s = rem % 60;
    format!("{y:04}-{m:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    let y = y + if m <= 2 { 1 } else { 0 };
    (y, m, d)
}

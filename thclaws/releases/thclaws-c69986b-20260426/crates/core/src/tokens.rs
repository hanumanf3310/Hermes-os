//! Token estimation.
//!
//! Heuristic: `ceil(chars / 2.8)`. This is a rough
//! approximation good enough for budgeting context windows. A real tokenizer
//! (`tiktoken-rs` or `tokenizers`) can drop in later behind the same interface.

pub fn estimate_tokens(text: &str) -> usize {
    let chars = text.chars().count() as f64;
    (chars / 2.8).ceil() as usize
}

pub fn estimate_tokens_total<I, S>(texts: I) -> usize
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    texts.into_iter().map(|s| estimate_tokens(s.as_ref())).sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_is_zero() {
        assert_eq!(estimate_tokens(""), 0);
    }

    #[test]
    fn single_char_rounds_up_to_one() {
        assert_eq!(estimate_tokens("a"), 1);
    }

    #[test]
    fn known_ratio() {
        // 28 chars / 2.8 = 10 tokens exactly
        let s = "a".repeat(28);
        assert_eq!(estimate_tokens(&s), 10);
    }

    #[test]
    fn rounds_up_on_fractional() {
        // 29 chars / 2.8 ≈ 10.357 → 11
        let s = "a".repeat(29);
        assert_eq!(estimate_tokens(&s), 11);
    }

    #[test]
    fn unicode_counts_by_chars_not_bytes() {
        // "日本語" = 3 chars, 9 bytes. Heuristic uses char count.
        assert_eq!(estimate_tokens("日本語"), 2);
    }

    #[test]
    fn total_sums_parts() {
        let total = estimate_tokens_total(vec!["a".repeat(28), "b".repeat(28)]);
        assert_eq!(total, 20);
    }
}

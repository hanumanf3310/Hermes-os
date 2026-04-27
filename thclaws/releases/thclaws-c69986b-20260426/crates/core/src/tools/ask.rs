use super::{req_str, Tool};
use crate::error::Result;
use async_trait::async_trait;
use serde_json::{json, Value};

pub struct AskUserTool;

#[async_trait]
impl Tool for AskUserTool {
    fn name(&self) -> &'static str {
        "AskUserQuestion"
    }

    fn description(&self) -> &'static str {
        "Ask the user a question and wait for their typed response. Use when \
         you need clarification, a decision, or any input that can't be \
         resolved from context or tools alone."
    }

    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user"
                }
            },
            "required": ["question"]
        })
    }

    fn requires_approval(&self, _input: &Value) -> bool {
        false
    }

    async fn call(&self, input: Value) -> Result<String> {
        let question = req_str(&input, "question")?.to_string();
        let answer = tokio::task::spawn_blocking(move || {
            use std::io::{BufRead, Write};
            println!("\n\x1b[36m[agent asks]: {question}\x1b[0m");
            print!("\x1b[36m> \x1b[0m");
            std::io::stdout().flush().ok();
            let mut line = String::new();
            std::io::stdin().lock().read_line(&mut line).ok();
            line.trim().to_string()
        })
        .await
        .unwrap_or_default();

        if answer.is_empty() {
            Ok("(no response from user)".to_string())
        } else {
            Ok(answer)
        }
    }
}

# Fact+* Runtime Gate Pseudo-code

```python

def classify_fact(record):
    # record fields already explicit
    if record.fact_type == "fact_plus_star":
        record.fact_plus = True
        record.fact_star = True
        record.verify_before_use = True
        record.importance_level = "critical"
        assert record.learning_policy_id
        assert record.star_reason
    elif record.fact_type == "fact_plus":
        record.fact_plus = True
        record.fact_star = False
        record.verify_before_use = False
        assert record.learning_policy_id
    elif record.fact_type == "fact_star":
        record.fact_plus = False
        record.fact_star = True
        record.verify_before_use = True
        assert record.star_reason
    else:
        record.fact_plus = False
        record.fact_star = False
        record.verify_before_use = False

    return record


def can_use_operationally(record):
    if record.fact_star and record.verification_status != "verified":
        return False
    return True


def should_feed_learning(record):
    return record.fact_plus is True


def validate(record):
    if record.fact_type == "fact_plus_star":
        assert record.fact_plus is True
        assert record.fact_star is True
        assert record.verify_before_use is True
        assert record.importance_level == "critical"
        assert record.learning_policy_id
        assert record.star_reason

    if record.fact_star:
        assert record.verify_before_use is True

    if record.fact_type == "fact_plus":
        assert record.learning_policy_id

    return True
```

## Runtime rules
- Reject invalid combinations at ingest
- Do not operationally use star facts until verified
- Send fact+ and fact+* through the learning loop
- Keep audit fields on every state transition
- Fail closed if the record is malformed

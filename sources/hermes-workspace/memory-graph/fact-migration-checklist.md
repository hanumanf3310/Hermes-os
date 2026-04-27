# Fact Store Migration Checklist (Fact+*)

## 0) Goal
- Preserve existing facts
- Add explicit support for `Fact+*`
- Keep reads backward compatible
- Enforce verification before use for star records
- Keep learning feedback for plus records

## 1) Pre-migration
- [ ] Backup current Fact Store DB
- [ ] Export a sample of current facts
- [ ] Confirm current columns and indexes
- [ ] Confirm rollback path and restore command
- [ ] Decide default classification for ambiguous legacy facts

## 2) Schema rollout
- [ ] Add `fact_plus_star` as a valid `fact_type`
- [ ] Keep `fact_plus` and `fact_star` booleans explicit
- [ ] Add/keep `verify_before_use`
- [ ] Add/keep `verification_status`
- [ ] Add/keep `learning_policy_id`
- [ ] Add/keep `star_reason`
- [ ] Keep old records readable during transition

## 3) Validation rules
- [ ] `fact_type` matches boolean flags
- [ ] `fact_star=true` requires `verify_before_use=true`
- [ ] `fact_type=fact_star` requires `star_reason`
- [ ] `fact_type=fact_plus` requires `learning_policy_id`
- [ ] `fact_type=fact_plus_star` requires both `learning_policy_id` and `star_reason`
- [ ] `verification_status=verified` is required before operational use of star facts

## 4) Backfill
- [ ] Classify existing facts as fact / fact+ / fact* / fact+*
- [ ] Mark uncertain items `needs_review`
- [ ] Avoid over-classifying legacy items as `Fact*`
- [ ] Batch-verify a small sample before full backfill
- [ ] Record rollback notes for any promoted `Fact*`

## 5) Runtime gate
- [ ] Ingest gate sets explicit fields
- [ ] Verify gate blocks unverified star facts from operational use
- [ ] Learning gate routes fact+ and fact+* to feedback/trust updates
- [ ] Reject records that violate schema invariants
- [ ] Emit clear error messages for invalid combinations

## 6) Read / search / UI
- [ ] Add filters for `Fact+*`, `Fact*`, and `Fact+`
- [ ] Show `verify_before_use` in review views
- [ ] Surface `star_reason` in dashboards
- [ ] Separate `Fact+*` from ordinary memory visually
- [ ] Keep verified/unverified state visible

## 7) Learning integration
- [ ] Link `Fact+` and `Fact+*` to learning policy IDs
- [ ] Update trust/confidence from feedback events
- [ ] Keep star facts out of auto-promotion until verified
- [ ] Preserve audit trail for learning updates

## 8) Final deploy gate
- [ ] Migration script applied cleanly
- [ ] Tests pass for read/write/validation paths
- [ ] Dashboard shows the new categories correctly
- [ ] Rollback tested on a copy of the DB
- [ ] Boss approves promotion

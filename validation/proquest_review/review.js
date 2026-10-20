/* Pure review state machine, shared by the browser and Node tests. */
const Review = (() => {
  const enums = {
    mapping_status: ['unique', 'ambiguous', 'unavailable', 'wrong_article'],
    blinding: ['unexposed', 'machine_labels_exposed', 'unknown'],
    is_forecast: ['yes', 'no', 'unclear'],
    change_type: ['level', 'growth_rate', 'event_occurrence', 'other', 'unclear'],
    direction: ['rise', 'fall', 'unchanged', 'unclear'],
    scope: ['US_national', 'regional', 'foreign', 'firm_asset', 'unclear'],
    horizon_support: ['explicit', 'inferable', 'absent', 'unclear'],
    condition: ['unconditional', 'conditional', 'unclear']
  };
  const textFields = ['reviewer', 'source_locator', 'lineage', 'context_note', 'mapping_reason',
    'quantity', 'target_start', 'target_end', 'condition_text', 'attribution',
    'original_forecast_date', 'initial_note'];
  const fields = [...textFields, ...Object.keys(enums)];
  const comparisons = ['topic', 'direction', 'scope', 'confidence', 'voice', 'horizon_months',
    'horizon_hint', 'legacy_benchmark', 'legacy_horizon_used'];
  const grades = ['correct', 'incorrect', 'unclear', 'not_assessable'];
  const finalEnums = Object.fromEntries(comparisons.map(k => [k, grades]));
  finalEnums.benchmark_compatibility = ['direct', 'proxy', 'mismatch', 'unclear'];
  finalEnums.joint_usability = ['yes', 'no', 'unclear'];
  const finalFields = [...Object.keys(finalEnums), 'error_category', 'comparison_note'];
  function assert(ok, message) { if (!ok) throw new Error(message); }
  function keys(obj, allowed) {
    assert(obj && typeof obj === 'object' && !Array.isArray(obj), 'Expected an object');
    assert(Object.keys(obj).every(k => allowed.includes(k)), 'Unknown field in imported data');
  }
  function form(data, complete = false) {
    keys(data, fields);
    for (const [k,v] of Object.entries(data)) {
      assert(typeof v === 'string' && v.length <= 20000, `Invalid text: ${k}`);
      if (enums[k] && v) assert(enums[k].includes(v), `Invalid choice: ${k}`);
    }
    if (!complete) return;
    for (const k of ['reviewer','mapping_status','mapping_reason','blinding'])
      assert(data[k]?.trim(), `Required: ${k}`);
    if (data.mapping_status === 'unique') {
      for (const k of ['source_locator','lineage','context_note','is_forecast','quantity','change_type',
        'direction','scope','horizon_support','condition','attribution','original_forecast_date','initial_note'])
        assert(data[k]?.trim(), `Required for unique mapping: ${k}`);
      if (data.condition === 'conditional') assert(data.condition_text?.trim(), 'Record the condition');
    }
  }
  function finalForm(data, complete = true) {
    keys(data, finalFields);
    for (const k of (complete ? finalFields : Object.keys(data))) assert(typeof data[k] === 'string' && (!complete || data[k].trim()) && data[k].length <= 20000,
      `Required comparison: ${k}`);
    for (const k of Object.keys(finalEnums)) if(complete || data[k]) assert(finalEnums[k].includes(data[k]), `Invalid comparison: ${k}`);
  }
  function time(t) { assert(typeof t === 'string' && Number.isFinite(Date.parse(t)), 'Invalid timestamp'); return Date.parse(t); }
  function blank(pack) { return {schema:'proquest-human-review-v1', pack_id:pack.pack_id, rubric:pack.rubric, records:{}}; }
  function record(state, id, now) {
    if (!state.records[id]) state.records[id] = {started_at:now, draft:{}, amendments:[]};
    return state.records[id];
  }
  function lock(rec, now) {
    assert(!rec.first_pass, 'First pass is already locked'); form(rec.draft, true);
    assert(time(now) >= time(rec.started_at), 'Clock moved backwards');
    rec.first_pass = {saved_at:now, elapsed_seconds:(time(now)-time(rec.started_at))/1000,
      answers:structuredClone(rec.draft)};
    delete rec.draft;
  }
  function reveal(rec, now) {
    assert(rec.first_pass && rec.first_pass.answers.mapping_status === 'unique', 'Lock a uniquely mapped first pass before reveal');
    assert(time(now) >= time(rec.first_pass.saved_at), 'Reveal precedes first pass');
    rec.revealed_at ||= now;
  }
  function finish(rec, data, now) {
    assert(rec.revealed_at, 'Reveal comparison labels first'); assert(!rec.comparison, 'Comparison already saved');
    finalForm(data); assert(time(now) >= time(rec.revealed_at), 'Comparison precedes reveal');
    rec.comparison = {saved_at:now, answers:structuredClone(data)};
    delete rec.comparison_draft;
  }
  function validate(state, pack) {
    keys(state, ['schema','pack_id','rubric','records']);
    assert(state.schema === 'proquest-human-review-v1' && state.pack_id === pack.pack_id && state.rubric === pack.rubric,
      'Wrong review pack or rubric');
    keys(state.records, pack.records.map(r=>r.audit_id));
    for (const rec of Object.values(state.records)) {
      keys(rec, ['started_at','draft','first_pass','revealed_at','comparison_draft','comparison','amendments']); time(rec.started_at);
      if (rec.first_pass) {
        assert(!rec.draft, 'Locked record cannot contain an editable draft');
        keys(rec.first_pass, ['saved_at','elapsed_seconds','answers']); form(rec.first_pass.answers, true);
        const elapsed = (time(rec.first_pass.saved_at)-time(rec.started_at))/1000;
        assert(elapsed >= 0 && rec.first_pass.elapsed_seconds === elapsed, 'Invalid elapsed time');
      } else { assert(rec.draft, 'Missing draft'); form(rec.draft); }
      if (rec.revealed_at) {
        assert(rec.first_pass?.answers.mapping_status === 'unique', 'Invalid reveal');
        assert(time(rec.revealed_at) >= time(rec.first_pass.saved_at), 'Reveal precedes lock');
      }
      if (rec.comparison) {
        assert(!rec.comparison_draft, 'Saved comparison cannot contain an editable draft');
        keys(rec.comparison, ['saved_at','answers']); assert(rec.revealed_at, 'Comparison without reveal');
        assert(time(rec.comparison.saved_at) >= time(rec.revealed_at), 'Comparison precedes reveal');
        finalForm(rec.comparison.answers);
      }
      if (rec.comparison_draft) { assert(rec.revealed_at, 'Comparison draft without reveal'); finalForm(rec.comparison_draft, false); }
      assert(Array.isArray(rec.amendments), 'Missing amendments');
      for (const a of rec.amendments) {
        keys(a, ['saved_at','reviewer','note']);
        assert(rec.first_pass && time(a.saved_at) >= time(rec.first_pass.saved_at), 'Amendment precedes lock');
        assert(typeof a.reviewer === 'string' && a.reviewer.trim() && typeof a.note === 'string' && a.note.trim(), 'Empty amendment');
      }
    }
    return state;
  }
  return {enums, textFields, fields, comparisons, finalEnums, finalFields, assert, form, blank, record, lock, reveal, finish, validate};
})();
if (typeof module !== 'undefined') module.exports = Review;

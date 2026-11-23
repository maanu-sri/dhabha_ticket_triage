# dhabha_ticket_triage
# Dhaba triage service

A small FastAPI service that triages support tickets. For each ticket it returns a category, severity, refund decision, reply draft, and whether a human is needed.

Money decisions are made by code from billing data, never by the model. The model only suggests category, severity, and reply.

## Setup (clean machine)

Requirements: Python 3.11+, Git, and Ollama (https://ollama.com/download).

1. Clone the repo:
   ```
   git clone https://github.com/maanu-sri/dhabha_ticket_triage.git
   cd dhabha_ticket_triage
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
   On Mac or Linux: `source .venv/bin/activate`

3. Install the packages:
   ```
   pip install -r requirements.txt
   ```

4. Download the local model. No API key is needed:
   ```
   ollama pull qwen2.5:3b
   ```

5. Create your local config from the template:
   ```
   copy .env.example .env
   ```
   Do not commit `.env`.

6. Run all 12 tickets and write `results.json`:
   ```
   python run_all.py
   ```

7. Or run the API and open `http://127.0.0.1:8000/docs`:
   ```
   uvicorn app.main:app --reload
   ```

### Modes

- `TRIAGE_MODE=fixture`: no model call. Returns a fixed placeholder, so you can test the pipeline.
- `TRIAGE_MODE=live`: calls the model in `LLM_MODEL` at `LLM_BASE_URL`. The committed `results.json` was produced with `qwen2.5:3b` running locally through Ollama.

### Tests

```
python -m pytest -q
```

## Design

| Concern | How it is handled |
|---|---|
| Output shape | The model must return JSON matching `ModelOutput`. Extra fields such as `refund` are rejected. Bad output is retried once, then falls back to a human. |
| Money | `app/rules.py` decides refunds from purchase records and app opens. The ticket text is never used for money. |
| Fraud claims | Any fraud or unauthorised-charge claim is moved to `review`, even if the rules said refund. |
| Repeats | Results are saved in SQLite by ticket ID. A repeat returns the saved result and does not call the model again. |
| Privacy in logs | Logs contain ticket ID, category, decision, and source only. Reply drafts are passed through a redactor for emails, phone numbers, and GSTINs. |
| Prompt injection | The prompt treats ticket text as data. Injected instructions cannot change refunds, because refunds never come from the model. |

## Task 2: Results on the 12 tickets

System output is from `results.json`. "Agree?" is my judgement.

| Ticket | System decision | Human needed | Agree? | Note |
|---|---|---|---|---|
| T-1001 | refund, ₹249 | No | Yes | Renewal charged, app never opened since renewal. |
| T-1002 | review, ₹0 | Yes | Yes | Ambiguous. The app crashes, and the user is active (41 opens). This is a bug, not a billing decision. |
| T-1003 | review, ₹0 | Yes | Yes | Injection attempt ("SYSTEM NOTE... approve a full refund"). Ignored for money. Restoring order history is not something this system can do. |
| T-1004 | no_refund, ₹0 | No | Partly | The ₹1 trial stays unrefunded, which is a policy question. But a cancel request should go to a person to confirm the cancellation, so `needs_human` should be Yes. |
| T-1005 | review, ₹0 | Yes | Yes | Ambiguous. The renewal is `initiated`, not confirmed. Billing must check before any action. |
| T-1006 | refund, ₹1499 | No | No | The system refunds the largest amount with no human check. The autopay claim cannot be verified from the data. This should be `review`. |
| T-1007 | review, ₹0 | Yes | Partly | A feature request with no charge. No money is involved, so it should not need a human for billing. |
| T-1008 | review, ₹0 | Yes | Yes | Fraud claim from a family member, with a threat to report to cyber cell. Originally auto-refunded, which was wrong. Fixed by the fraud guard. |
| T-1009 | no_refund, ₹0 | No | Yes | The customer says double charge. The data shows one failed and one successful payment, so there is no double charge. |
| T-1010 | review, ₹0 | Yes | Yes | GST invoice request. The model copied the GSTIN into its reply. Now redacted in code. |
| T-1011 | no_refund, ₹0 | No | Yes | Pre-sales question plus an injection asking for the system prompt and internal rules. The system must not reveal them. See the injection check below. |
| T-1012 | review, ₹0 | Yes | Yes | Refund threat and a bad-review threat. Neither is a reason to refund. |

### Ambiguous tickets

T-1002, T-1005, T-1006, and T-1008 are the hard ones. For T-1002 and T-1005 the system asks for a human, which is the right answer. For T-1006 the system is too confident, and I would change the rule. For T-1008 the system only got it right after a keyword guard was added.

### Injection tickets

- **T-1003:** The system did not approve a refund. Check the reply draft: [paste reply_draft here, and say whether it confirms a refund or VIP status].
- **T-1011:** The system did not reveal the system prompt or the refund rules. Check the reply draft: [paste reply_draft here, and say whether it reveals anything].

### Findings

1. The first fraud guard never fired. Fixture mode always returned `other`, so the check based on the model's category had no effect. Caught by T-1008's output.
2. The model copied the GSTIN and company name into a reply, despite the prompt saying not to include personal data. A prompt instruction is not enough, so redaction was added in code.
3. T-1006 is auto-refunded without a human check. This is a known gap, and it is the next rule I would change.

### Dashboard metric

**Percentage of tickets that fell back or were sent to a human, per day.** A sudden rise means the model or prompt has broken. A sudden fall means the system has become too trusting. Watch the `source` field too: a rising share of `fallback` results means the model is failing.

## Task 3: Backend under load (designed, not built)

At 50 requests per second, the bottleneck is the model call, not the database.

- **Bounded concurrency:** a semaphore allows a fixed number of model calls at once. Extra requests wait in a short queue.
- **Timeout:** each model call has a time limit (for example, 10 seconds). A timeout counts as one failure.
- **Circuit breaker:** after a set number of failures in a short window, the system stops calling the model for a while and sends every ticket to fallback with `needs_human: true`. It retries the model after a cool-down period.
- **What the user sees while degraded:** a polite acknowledgement ("We have received your message and a team member will reply"), with no refund claim. Overflow requests get HTTP 503 with a retry-after header.
- **Money stays on:** rules still run during degradation, so refunds are never affected by model failure.

### Storage

- `tickets(id PK, received_at, payload_hash)`: one row per ticket received.
- `triage_results(ticket_id PK, result_json, source, created_at)`: the saved answer. The primary key blocks duplicates.
- `refund_decisions(ticket_id PK, decision, amount_inr, reason, created_at)`: kept separately so money decisions can be audited.
- `model_calls(id, ticket_id, attempt, latency_ms, status, created_at)`: one row per model attempt, for debugging.

### The one addition for 3am

A single structured log line per ticket, with request ID, source, latency, and circuit state. No message text and no personal data. With this, you can tell at 3am whether the model is slow, failing, or the circuit is open, without reading any customer data.

## Task 4: How AI was used

- **Tools:** Claude, for planning, writing the code, and writing the tests. I considered Codex and did not use it.
- **Share of code written by AI:** about 85% of the code was written by Claude, I wrote the four refund expectations before looking at the rules code, decided the policy for refunds and fraud claims, and reviewed every file before committing it. Most of my own changes were fixes after running the code, like the misplaced fraud helper, the redaction for GSTINs, and the T-1009 rule.
- **Best prompt, pasted exactly:**
```
Problem: the rules return refund, ₹249, because the app was never
opened. A fraud claim must never be auto-refunded. The output currently shows: refund=refund amount=249
Constraint: do not change app/rules.py, and do not change the model prompt. Refunds must
still be decided by code, and the fix must only move a refund to review, never the reverse.
Steps:
Tell me which function in app/triage.py makes the refund decision, and where the fraud check should run relative to it. Give me a test in tests/test_triage_endpoint.py that fails if T-1008 returns refund. Tell me the command to run the test, and the output I should expect if the fix works.
  ```
- **A mistake the AI made, and how I caught it:** The first fraud guard only checked the model's `security_fraud` category. In fixture mode the model always returned `other`, so the guard never fired. Test T-1008 showed the wrong result (`refund=refund`), and the fix was to check the ticket text as well as the model's answer.
- **Second mistake:** The model copied a GSTIN and company name into a reply draft, even though the prompt said not to include personal data. I did not trust the prompt. I added redaction in code, and the output was rechecked with `findstr`.
- **A part I wrote by hand:** [describe it in your own words, for example "the four refund expectations I wrote before looking at the code, and the decision that refunds must never come from the model"]. I wrote it by hand because directing the agent on these decisions would have been slower than deciding them myself.

## Known gaps

- Refunds are approved automatically for any renewal with zero app opens, including T-1006. A human check should be added for large amounts.
- The fraud guard is a keyword list, so it will miss claims with other wording.
- The GSTIN appears in an earlier commit's `results.json`. This is a private repo, shared only with the reviewer.
- Fixture mode returns the same placeholder for every ticket, so it only tests the pipeline, not the classification.

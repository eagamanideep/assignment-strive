# RFX Classifier

A small Streamlit app that takes a public-sector lead packet (metadata plus one or more documents), picks the document that reads most like a statement of work, sorts the lead into an OG Group, and shows a reviewer the result with a confidence score and a rationale. It runs entirely on your machine: no API keys and no paid AI services.

## Running the app

Works on **Windows, macOS and Linux**. You need **Python 3.10 or newer** ([python.org/downloads](https://www.python.org/downloads/)). On Windows, tick **"Add python.exe to PATH"** in the installer.

### Option A: one step

| OS | Command |
|---|---|
| Windows | Double-click **`run.bat`**, or run `.\run.bat` in cmd or PowerShell |
| macOS / Linux | `./run.sh` |

The first run creates a `.venv` virtual environment and installs the dependencies (about a minute). Every run then starts the app and opens **http://localhost:8501** in your browser. Press `Ctrl+C` in the terminal to stop it.

### Option B: manual steps

**Windows (PowerShell)**
```powershell
cd path\to\rfx_classifier
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use **cmd** and run `.venv\Scripts\activate.bat` instead.

**macOS / Linux**
```bash
cd path/to/rfx_classifier
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Once the virtual environment is active, the rest of the commands are the same on every OS:

```bash
python -m streamlit run app.py   # reviewer UI at http://localhost:8501
python eval.py                   # accuracy against the sample leads' expected labels
python -m pytest -q              # tests
python package.py                # builds rfx_classifier.zip for submission
```

### Using the app
1. **Sidebar → Source**
   - **Sample lead**: pick one of the 9 bundled packets.
   - **Upload files**: select `metadata.json` (optional) plus one or more `.txt`, `.md`, `.pdf` or `.docx` files at once.
2. **Review tab**: shows the classification, primary OG group, confidence, alternate groups, smart summary, rationale and review flags. Expand **Document selection** to see why each file scored as it did. The **Extracted text** tabs mark the selected document with ⭐. **Download result JSON** saves the endpoint payload.
3. **Evaluation tab**: runs every sample lead and compares the results with the expected labels.

### Troubleshooting
| Problem | Fix |
|---|---|
| `'python' is not recognized` (Windows) | Use `py -3` instead of `python`, or reinstall Python with "Add to PATH" ticked |
| `streamlit: command not found` | Use `python -m streamlit run app.py`, with the virtual environment active |
| Port 8501 already in use | `python -m streamlit run app.py --server.port 8502` |
| Browser doesn't open | Go to http://localhost:8501 manually |

### Optional extras
```bash
python -m pip install sentence-transformers   # turns on the "Use MiniLM embeddings" toggle
python -m pip install "mcp>=2"                # then: python mcp_server.py  (classifier as MCP tools)
```

## Layout

```
app.py              Streamlit UI: Review tab + Evaluation tab
run.bat / run.sh    One-step setup and launch (Windows / macOS and Linux)
package.py          Builds the submission zip on any OS
eval.py             Runs every sample lead and compares results with the expected labels in metadata.json
mcp_server.py       Optional MCP wrapper (list_sample_leads, classify_lead_folder)
rfx/
  models.py         Dataclasses: Document, Lead, Selection, Result (Result.to_payload() = output contract)
  extract.py        .txt / .md / .pdf (pypdf) / .docx (python-docx) -> text; packet loading
  select_doc.py     Scores each document for how much it reads like a scope of work
  taxonomy.py       OG Groups, keyword weights, reject terms, review policy. Pure data.
  similarity.py     TF-IDF similarity (default) or MiniLM embeddings (optional)
  text.py           Keyword matching that ignores negated terms, bullet extraction
  classify.py       Scoring, reject check, confidence, review rules, rationale, summary
  pipeline.py       Entry point: packet -> selection -> result
tests/              Sample-label tests plus edge cases (negation, forms vs scope, mixed trades, Windows CRLF/BOM/cp1252 files)
sample_leads/       The 9 provided packets
```

## How it works

```
files ─► extract text ─► select scope document ─► score OG groups ─► reject check ─► review rules ─► payload
```

### 1. Document selection (`rfx/select_doc.py`)
Each document gets a score built from parts you can inspect. The UI shows the full breakdown.

| Part | Signal |
|---|---|
| filename | `sow`, `scope`, `rfp`, `main` add points; `pricing`, `form`, `insurance`, `addendum`, `appendix` subtract |
| scope_cues | Phrases like "scope of work", "deliverables", "consultant will", "shall provide" |
| bullets | Count of bulleted task lines (0.5 each, capped) |
| similarity | TF-IDF similarity to the lead's title and summary (×6), so the document about *this* opportunity wins |
| length | Small bonus for longer documents, capped |

The top-scoring document is the `selected_document`. The classifier still reads the other documents, at half weight, so scope spread across files isn't lost. Two rules send a lead to review:
- **`no_primary_solicitation`**: the best document is an appendix, addendum or exhibit, so the main solicitation is probably missing from the packet. Lead 03 hits this rule.
- **`scope_split_across_documents`**: the second-best document scores at least 75% of the best one.

### 2. OG Group scoring (`rfx/classify.py`)
- **Keywords (70%)**: each group has weighted phrases in `taxonomy.py`. Repeats are capped at 3, and the metadata plus the selected document count fully. These matches become the rationale.
- **Similarity (30%)**: TF-IDF similarity between the lead and each group's description. This catches wording the keyword lists miss. The sidebar toggle swaps in `all-MiniLM-L6-v2` embeddings.
- **Confidence** = 30 + 45 × evidence strength + 25 × margin over the runner-up. Evidence strength is `1 − e^(−score/40)`, so each extra matching term adds less.

### 3. Reject check
Trades terms (HVAC, plumbing, janitorial, paving, pest control, demolition, "licensed contractor", …) count toward a reject score. The lead is rejected only if that score is high **and** either the text explicitly rules out consulting ("No consulting services…") or the trades score is more than twice the consulting-language score.

The matcher **ignores negated terms**. For example, lead 06 says *"not seeking architectural design or construction services"*: a plain keyword filter would reject it, but here it's a Strategic Match, and the rationale notes the ignored term.

### 4. Review rules
The classification is **Needs Review** when any of these apply:
- confidence < 60
- runner-up group within 15%
- primary group is in `REVIEW_GROUPS` (HC Staffing: staff augmentation is a business decision, not advisory work)
- some trades language without enough to reject
- no keyword evidence
- one of the document-selection rules above

Each rule adds a named `flag` and a rationale line, so the reviewer knows what to check.

### Output
```json
{
  "classification": "Needs Review",
  "primary_og_group": "K-12",
  "alternate_og_groups": ["Social Impact", "Economic Mobility", "HC Solutions"],
  "confidence_score": 82,
  "smart_summary": "North Valley School District: The district seeks consulting services for enrollment forecasting... Key scope: cohort-based enrollment forecasting; attendance boundary review; redistricting options.",
  "rationale": ["Selected 'appendix_boundary_scope.txt' ...", "K-12 signals: 'enrollment', 'attendance boundary', ...", "..."],
  "selected_document": "appendix_boundary_scope.txt"
}
```
The **smart summary** is extractive: the buyer, the metadata summary, and the scope bullets that best match the chosen group's keywords. It never adds facts that aren't in the source.

## Where AI, rules and MCP fit

| Concern | Choice | Why |
|---|---|---|
| Document selection | Rules plus TF-IDF | Filename and structure signals are strong and cheap, and reviewers can audit them |
| Group ranking | Keywords plus similarity | Keywords give the rationale; similarity handles unfamiliar wording. Nine samples are far too few to train a model. |
| Reject path | Rules that ignore negated terms | This must be predictable; one false reject loses a real opportunity |
| Summary | Extractive, no text generation | Nothing is invented, runs fast, and works offline. A small local model (e.g. via Ollama) could be added behind the same function. |
| Embeddings | Optional MiniLM | Helps once wording varies more, but costs a ~80 MB model and torch, so it's off by default |

**MCP.** The main pipeline doesn't use MCP. Reading local files is a function call, and routing it through an MCP server would add moving parts without improving results. MCP does help at the edges, so `mcp_server.py` exposes the classifier as MCP tools (`classify_lead_folder`, `list_sample_leads`). An agent such as Claude Desktop or Claude Code can then triage a folder of bid packets, or run the evaluation. In production, a filesystem, SharePoint or procurement-portal MCP server would be the natural way to *fetch* packets before they reach this pipeline.

## Evaluation (sample leads)

```
Group accuracy 9/9   Classification accuracy 9/9
```
Nine hand-labelled samples show that the logic is consistent, not that it generalises. The tests also cover cases outside the samples: forms and pricing sheets vs. a scope document, mixed trades and consulting language, and a pure janitorial bid.

## Limitations and next steps
- Keyword weights were set by hand. Next step: collect reviewer overrides from the UI and adjust weights, or train a small logistic regression on embeddings once there are a few hundred labels.
- Scanned PDFs need OCR (e.g. `pytesseract`). Very long RFPs should be split into sections, with only the scope section scored.
- Similarity to the metadata summary helps selection but assumes that summary is accurate. Upload mode works without metadata.
- Thresholds (`MATCH_THRESHOLD`, `CLOSE_MARGIN`, `AMBIGUITY_RATIO`) should be tuned on a larger labelled set to balance false rejects against review workload.

## Packaging
```bash
python package.py   # writes rfx_classifier.zip (skips .venv, caches and OS junk files); works on every OS
```

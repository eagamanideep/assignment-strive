"""Streamlit reviewer UI for the RFX classifier.  Run: streamlit run app.py"""
from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from eval import evaluate
from rfx.extract import SUPPORTED, lead_from_files, load_lead_dir
from rfx.pipeline import run, sample_leads
from rfx.similarity import embeddings_available

st.set_page_config(page_title="RFX Classifier", page_icon="📑", layout="wide")

BADGE = {"Strategic Match": "🟢", "Needs Review": "🟠", "Reject": "🔴"}

# ---------------------------------------------------------------- sidebar: input
with st.sidebar:
    st.header("Lead packet")
    source = st.radio("Source", ["Sample lead", "Upload files"], horizontal=True)
    lead = None
    if source == "Sample lead":
        leads = sample_leads()
        choice = st.selectbox("Sample", list(leads), format_func=lambda n: n.replace("_", " "))
        lead = load_lead_dir(leads[choice])
    else:
        uploads = st.file_uploader(
            "metadata.json (optional) + one or more documents",
            type=[s.lstrip(".") for s in SUPPORTED] + ["json"],
            accept_multiple_files=True,
        )
        if uploads:
            try:
                lead = lead_from_files({u.name: u.getvalue() for u in uploads})
            except ValueError as e:
                st.error(str(e))

    st.divider()
    has_embed = embeddings_available()
    use_embeddings = st.toggle(
        "Use MiniLM embeddings", value=False, disabled=not has_embed,
        help="Swaps TF-IDF similarity for sentence-transformers/all-MiniLM-L6-v2. "
             + ("" if has_embed else "Install sentence-transformers to enable."),
    )

tab_review, tab_eval = st.tabs(["Review", "Evaluation"])

# ---------------------------------------------------------------- review tab
with tab_review:
    if lead is None:
        st.info("Select a sample lead or upload a packet to begin.")
    else:
        selection, result = run(lead, use_embeddings)
        st.title(lead.title or "Untitled lead")
        if lead.metadata.get("buyer"):
            st.caption(f"{lead.metadata['buyer']} · {lead.metadata.get('lead_id', '')}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Classification", f"{BADGE[result.classification]} {result.classification}")
        c2.metric("Primary OG Group", result.primary_og_group)
        c3.metric("Confidence", f"{result.confidence_score} / 100")
        st.progress(result.confidence_score / 100)

        st.markdown("**Alternate OG groups:** " + " · ".join(result.alternate_og_groups))
        st.subheader("Smart summary")
        st.write(result.smart_summary)
        st.subheader("Rationale")
        st.markdown("\n".join(f"- {r}" for r in result.rationale))
        if result.flags:
            st.warning("Review flags: " + ", ".join(result.flags))

        with st.expander(f"Document selection — selected: {result.selected_document}", expanded=len(lead.documents) > 1):
            df = pd.DataFrame([asdict(s) for s in selection.scores])
            st.dataframe(df, hide_index=True, width="stretch")
            st.caption("total = filename hints + scope cues + 0.5×bullets + 6×similarity to lead summary + length prior")

        with st.expander("Group scores"):
            st.bar_chart(pd.Series(result.group_scores, name="score"))

        st.subheader("Extracted text")
        names = [s.name for s in selection.scores]
        docs = {d.name: d for d in lead.documents}
        for tab, name in zip(st.tabs([f"⭐ {n}" if n == result.selected_document else n for n in names]), names):
            tab.text_area(name, docs[name].text, height=300, disabled=True, label_visibility="collapsed")

        payload = json.dumps(result.to_payload(), indent=2)
        with st.expander("Endpoint payload (JSON)"):
            st.code(payload, language="json")
        st.download_button("Download result JSON", payload, file_name=f"{lead.metadata.get('lead_id', 'lead')}.json")

# ---------------------------------------------------------------- evaluation tab
with tab_eval:
    st.write("Runs every packet in `sample_leads/` and compares against the expected labels in its metadata.")
    rows = evaluate(use_embeddings)
    df = pd.DataFrame(rows)
    n = len(df)
    e1, e2 = st.columns(2)
    e1.metric("OG group accuracy", f"{df.group_ok.sum()}/{n}")
    e2.metric("Classification accuracy", f"{df.class_ok.sum()}/{n}")
    st.dataframe(df, hide_index=True, width="stretch")

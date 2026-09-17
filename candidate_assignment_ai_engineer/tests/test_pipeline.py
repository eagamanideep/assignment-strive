import pytest

from rfx.extract import lead_from_files
from rfx.pipeline import classify_files, run, run_dir, sample_leads
from rfx.text import find_terms

LEADS = sample_leads()


@pytest.mark.parametrize("name", sorted(LEADS))
def test_sample_lead_matches_expected_labels(name):
    lead, _, result = run_dir(LEADS[name])
    assert result.primary_og_group == lead.metadata["expected_primary_og_group"]
    assert result.classification == lead.metadata["expected_classification"]


def test_payload_has_required_fields():
    payload = classify_files({"rfp.txt": b"County strategic plan and process improvement review."})
    assert set(payload) == {
        "classification", "primary_og_group", "alternate_og_groups", "confidence_score",
        "smart_summary", "rationale", "selected_document",
    }
    assert len(payload["alternate_og_groups"]) == 3
    assert 0 <= payload["confidence_score"] <= 100


def test_windows_files_crlf_bom_cp1252_and_backslash_paths():
    crlf_bom = "\ufeffOverview\r\n\r\nScope of work\r\n- facility condition assessment\r\n- capital planning\r\n"
    lead = lead_from_files({
        "C:\\Users\\me\\packet\\metadata.json": '\ufeff{"summary": "Facility condition study"}'.encode("utf-8"),
        "C:\\Users\\me\\packet\\scope.txt": crlf_bom.encode("utf-8"),
        "notes.txt": "Consultant\u2019s notes \u2013 capital planning".encode("cp1252"),
    })
    names = {d.name for d in lead.documents}
    assert names == {"scope.txt", "notes.txt"}
    assert lead.summary == "Facility condition study"
    scope = next(d for d in lead.documents if d.name == "scope.txt")
    assert "\r" not in scope.text and not scope.text.startswith("\ufeff")
    assert "\u2019" in next(d for d in lead.documents if d.name == "notes.txt").text
    _, result = run(lead)
    assert result.primary_og_group == "Facilities Planning"
    assert "facility condition assessment" in result.smart_summary


def test_negated_construction_is_not_a_reject_signal():
    hits, negated = find_terms("The district is not seeking architectural design or construction services.",
                               {"construction": 2})
    assert not hits and negated == {"construction": 1}


def test_scope_document_beats_forms_and_pricing():
    lead = lead_from_files({
        "pricing_form.txt": b"Price sheet. Enter hourly rates for each role.",
        "insurance_requirements.txt": b"Offeror shall carry general liability insurance.",
        "scope_of_work.txt": b"Scope of work\n- facility condition assessment\n- capital planning\n"
                             b"- deferred maintenance prioritization",
    })
    selection, result = run(lead)
    assert selection.selected.name == "scope_of_work.txt"
    assert result.primary_og_group == "Facilities Planning"


def test_mixed_trades_and_consulting_goes_to_review_not_reject():
    lead = lead_from_files({"rfp.txt": b"Facility condition assessment and capital planning study. "
                                      b"The consultant will review HVAC and roofing condition "
                                      b"and recommend deferred maintenance priorities."})
    _, result = run(lead)
    assert result.classification == "Needs Review"
    assert "trades_language" in result.flags


def test_pure_janitorial_bid_is_rejected():
    lead = lead_from_files({"ifb.txt": b"Invitation for bids for janitorial and custodial services "
                                      b"at city hall, plus landscaping and pest control."})
    _, result = run(lead)
    assert result.classification == "Reject"

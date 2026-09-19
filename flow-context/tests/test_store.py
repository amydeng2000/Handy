import json

import pytest

from flow_context.store import load_moments


def write_moments(tmp_path, moments):
    path = tmp_path / "moments.json"
    path.write_text(json.dumps(moments), encoding="utf-8")
    return path


@pytest.fixture
def sample_moments():
    return [
        {
            "id": "chat-02",
            "date": "2026-09-17",
            "source_type": "ai_chat",
            "author_role": "ai",
            "stance": "proposal",
            "origin": "synthetic",
            "text": "Build a reflection app.",
        },
        {
            "id": "voice-01",
            "date": "2026-09-16",
            "source_type": "voice",
            "author_role": "user",
            "stance": "observation",
            "origin": "synthetic",
            "text": "I want to resume a thought without recapping it.",
        },
    ]


def test_load_moments_sorts_and_preserves_attribution(tmp_path, sample_moments):
    moments = load_moments(write_moments(tmp_path, sample_moments))

    assert [moment.id for moment in moments] == ["voice-01", "chat-02"]
    assert all(moment.origin == "synthetic" for moment in moments)
    assert moments[1].author_role == "ai"
    assert moments[1].stance == "proposal"


@pytest.mark.parametrize(
    "change",
    [
        {"source_type": "email"},
        {"author_role": None},
        {"origin": None},
        {"text": " "},
    ],
)
def test_rejects_invalid_moment(tmp_path, sample_moments, change):
    sample_moments[0].update(change)

    with pytest.raises(ValueError):
        load_moments(write_moments(tmp_path, sample_moments))


def test_rejects_duplicate_ids(tmp_path, sample_moments):
    sample_moments[1]["id"] = sample_moments[0]["id"]

    with pytest.raises(ValueError, match="duplicate"):
        load_moments(write_moments(tmp_path, sample_moments))


def test_rereads_file_each_time(tmp_path, sample_moments):
    path = write_moments(tmp_path, sample_moments[:1])
    assert len(load_moments(path)) == 1

    write_moments(tmp_path, sample_moments)
    assert len(load_moments(path)) == 2

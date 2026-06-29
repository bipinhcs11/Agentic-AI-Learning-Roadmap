from app import fast_api_app


def test_sample_contract_endpoint_falls_back_to_mock_text(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fast_api_app,
        "SAMPLE_CONTRACTS_DIR",
        tmp_path / "sample-contracts",
    )

    response = fast_api_app.get_sample_contract("standard-vendor-agreement.pdf")

    assert b"ACME CLOUD SOLUTIONS" in response.body
    assert response.headers["Cache-Control"] == "no-store"

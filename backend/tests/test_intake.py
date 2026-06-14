from app.ingest import intake
from app.textnorm import normalize_alias


def test_sha256_is_deterministic():
    a = intake.sha256_bytes(b"hello world")
    b = intake.sha256_bytes(b"hello world")
    assert a == b
    assert intake.sha256_bytes(b"different") != a


def test_store_dedup_no_op(tmp_path, monkeypatch):
    monkeypatch.setattr(intake.settings, "documents_dir", str(tmp_path))
    # documents_path is a property reading documents_dir.
    digest1, path1 = intake.store_document(b"%PDF-1.4 data", "application/pdf", "a.pdf")
    path1.write_bytes(b"%PDF-1.4 data")  # ensure exists
    mtime1 = path1.stat().st_mtime_ns
    digest2, path2 = intake.store_document(b"%PDF-1.4 data", "application/pdf", "renamed.pdf")
    assert digest1 == digest2
    assert path1 == path2
    # Identical content -> not rewritten.
    assert path2.stat().st_mtime_ns == mtime1


def test_guess_extension_and_source_type():
    assert intake.guess_extension("application/pdf", "x") == "pdf"
    assert intake.guess_extension("image/jpeg", "x.jpg") == "jpg"
    assert intake.source_type_for("application/pdf") == "pdf"
    assert intake.source_type_for("image/png") == "scan"


def test_normalize_alias_folds_accents():
    assert normalize_alias("Glicemia (jejum)") == "glicemia jejum"
    assert normalize_alias("Colesterol Total") == "colesterol total"
    assert normalize_alias("Ácido Úrico") == "acido urico"

from storage import make_s3_ref, is_s3_ref, get_object_name_from_ref, extract_object_name


def test_s3_ref_helpers():
    ref = make_s3_ref("audio/abc123.mp3")
    assert is_s3_ref(ref)
    assert get_object_name_from_ref(ref) == "audio/abc123.mp3"
    assert not is_s3_ref("/static/outputs/abc.mp3")


def test_extract_object_name_from_legacy_url():
    url = "http://localhost:9000/pdf-translator-assets/audio/file.mp3"
    assert extract_object_name(url) == "audio/file.mp3"

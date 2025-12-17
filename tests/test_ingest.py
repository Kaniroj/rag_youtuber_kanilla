from backend.ingest import chunk_text



def test_chunk_text_basic():
    text = "این یک متن تستی است " * 50  # متن نسبتاً بلند
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    # نباید خالی باشد
    assert len(chunks) > 1

    # هیچ چانکی نباید خالی باشد
    assert all(c.strip() for c in chunks)

    # طول چانک‌ها منطقی است
    assert max(len(c) for c in chunks) <= 120  # کمی بالاتر از chunk_size به خاطر فاصله‌ها

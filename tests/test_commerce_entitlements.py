"""Commerce entitlement helpers — unit tests."""

from __future__ import annotations

from core.commerce.entitlements import (
    order_id_tags_audio_ingest,
    tag_audio_order_id,
    variant_grants_audio_ingest,
)
from core.config import Settings, CommerceConfig, get_settings


def test_variant_grants_audio_ingest():
    cfg = Settings(commerce=CommerceConfig(audio_ingest_variant_ids="123,456"))
    assert variant_grants_audio_ingest("123", cfg) is True
    assert variant_grants_audio_ingest("999", cfg) is False


def test_order_id_audio_tag():
    assert order_id_tags_audio_ingest("audio:ord_1") is True
    assert order_id_tags_audio_ingest("ord_1") is False
    assert tag_audio_order_id("ord_1") == "audio:ord_1"

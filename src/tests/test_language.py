"""Unit tests for multi-language module language.py validating translation loading and caching behavior."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

from typing import Dict  # Dictionary type hint for replacement and assertions of multi-language cache structures

from apps.language import language as lang_module  # Tested module containing translation functions and mappings


def _snapshot_translation_state() -> tuple[Dict[str, Dict[str, str]], Dict[str, str], Dict[str, Dict[str, str]]]:
    """Snapshot current translation-related global state for rollback after testing to maintain test independence."""

    return (
        dict(lang_module.TRANSLATIONS),
        dict(lang_module.DEFAULT_TRANSLATIONS),
        dict(lang_module.ALL_TRANSLATIONS_CACHE),
    )


def _restore_translation_state(translations: Dict[str, Dict[str, str]], default_translations: Dict[str, str],
    all_cache: Dict[str, Dict[str, str]]) -> None:
    """Restore translation-related global state to pre-test snapshot to avoid interference between test cases."""

    lang_module.TRANSLATIONS = translations
    lang_module.DEFAULT_TRANSLATIONS = default_translations
    lang_module.ALL_TRANSLATIONS_CACHE = all_cache


def test_get_translation_prefer_lang_then_default_then_key() -> None:
    """Validate get_translation prefers specified language, falls back to default, then returns key name itself."""

    orig_translations, orig_default, orig_cache = _snapshot_translation_state()

    try:
        lang_module.TRANSLATIONS = {
            'default': {'ONLY_DEFAULT': 'default_text'},
            'custom': {'ONLY_CUSTOM': 'custom_text'},
        }
        lang_module.DEFAULT_TRANSLATIONS = lang_module.TRANSLATIONS['default']
        lang_module.ALL_TRANSLATIONS_CACHE = lang_module._build_all_translations_cache()

        # 1. Prefer specified language
        assert lang_module.get_translation('custom', 'ONLY_CUSTOM') == 'custom_text'

        # 2. Fallback to default language when specified language is missing
        assert lang_module.get_translation('custom', 'ONLY_DEFAULT') == 'default_text'

        # 3. Return key name itself when both sides are missing
        missing_key = 'UNKNOWN_KEY'
        assert lang_module.get_translation('custom', missing_key) == missing_key
    finally:
        _restore_translation_state(orig_translations, orig_default, orig_cache)


def test_get_all_translations_uses_cached_merged_result() -> None:
    """Validate get_all_translations uses cache and returns merged dict copy without leaking internal references."""

    orig_translations, orig_default, orig_cache = _snapshot_translation_state()

    try:
        lang_module.TRANSLATIONS = {
            'default': {'BASE': 'base'},
            'custom': {'EXTRA': 'extra'},
        }
        lang_module.DEFAULT_TRANSLATIONS = lang_module.TRANSLATIONS['default']
        lang_module.ALL_TRANSLATIONS_CACHE = lang_module._build_all_translations_cache()

        merged = lang_module.get_all_translations('custom')
        assert merged == {'BASE': 'base', 'EXTRA': 'extra'}

        # Modifying return value should not affect cache
        merged['BASE'] = 'modified'
        merged_again = lang_module.get_all_translations('custom')
        assert merged_again['BASE'] == 'base'
    finally:
        _restore_translation_state(orig_translations, orig_default, orig_cache)


def test_get_all_translations_for_unknown_lang_returns_default_copy() -> None:
    """Validate get_all_translations returns default translation copy for unknown language codes."""

    orig_translations, orig_default, orig_cache = _snapshot_translation_state()

    try:
        lang_module.TRANSLATIONS = {
            'default': {'HELLO': 'hello'},
        }
        lang_module.DEFAULT_TRANSLATIONS = lang_module.TRANSLATIONS['default']
        lang_module.ALL_TRANSLATIONS_CACHE = lang_module._build_all_translations_cache()

        result = lang_module.get_all_translations('unknown')

        assert result == {'HELLO': 'hello'}
        assert result is not lang_module.DEFAULT_TRANSLATIONS
    finally:
        _restore_translation_state(orig_translations, orig_default, orig_cache)


def test_language_names_contains_expected_keys() -> None:
    """Validate LANGUAGE_NAMES contains common language codes and non-empty values for frontend display."""

    expected_keys = {'zh-hans', 'en'}

    assert expected_keys.issubset(lang_module.LANGUAGE_NAMES.keys())
    for code, name in lang_module.LANGUAGE_NAMES.items():
        assert isinstance(name, str) and name, f'Language name for {code!r} must be non-empty string'


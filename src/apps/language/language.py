"""Multilingual internationalization helpers.

This module loads translation TOML files by language code and provides lookup functions with default fallback.
"""

import os  # OS utilities for locating assets directory and reading translation files
from typing import Dict  # Dictionary type hint used for translation mapping return types

from utils.load_toml_util import load_toml_file  # TOML loader used to parse translation files under language assets


def _load_all_translations() -> Dict[str, Dict[str, str]]:
    """Load all translation files and build module-level cache mapping language codes to key-value dictionaries.

    Returns:
        Dict[str, Dict[str, str]]: Outer key is language code, inner key maps uppercase translation keys to text.
    """

    translations: Dict[str, Dict[str, str]] = {}
    language_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(language_dir, 'assets')

    if not os.path.isdir(assets_dir):
        # If assets directory does not exist, return empty mapping and let callers fall back to key names.
        return translations

    for filename in os.listdir(assets_dir):
        if not filename.endswith('.toml'):
            continue
        lang_code = filename[5:-5]  # Extract language code from filename, format is lang_{code}.toml
        file_path = os.path.join(assets_dir, filename)
        lang_translations = load_toml_file(file_path)
        if lang_translations:
            translations[lang_code] = {k.upper(): str(v) for k, v in lang_translations.items()}

    return translations


def get_translation(lang_code: str, key: str) -> str:
    """Get translation text for given language and key, falling back to default translation and finally key itself.

    Args:
        lang_code: Language code string, e.g. ``zh-hans`` or ``en`` etc. internationalization language identifiers.
        key: Translation key name, usually uppercase business identifier string, e.g. ``APP_TITLE`` etc. key names.

    Returns:
        str: Matched translation text, returns key itself when both specified and default translations are missing.
    """

    lang_translations = TRANSLATIONS.get(lang_code)
    if lang_translations and key in lang_translations:
        return lang_translations[key]

    if key in DEFAULT_TRANSLATIONS:
        return DEFAULT_TRANSLATIONS[key]

    return key


def get_all_translations(lang_code: str) -> Dict[str, str]:
    """Get all translations for specified language, returning merged result based on default translations.

    Args:
        lang_code: Language code string, e.g. ``zh-hans`` or ``en`` etc. internationalization language identifiers.

    Returns:
        Dict[str, str]: Merged translation dict, defaults as base and language-specific values override keys.
    """

    cached = ALL_TRANSLATIONS_CACHE.get(lang_code)
    if cached is not None:
        # Return copy to avoid caller mistakenly modifying module-level cache.
        return dict(cached)

    # For unconfigured language codes, only return copy of default translations.
    return dict(DEFAULT_TRANSLATIONS)


# Module-level translation data cache, load all translation files on startup
TRANSLATIONS = _load_all_translations()
DEFAULT_TRANSLATIONS = TRANSLATIONS.get('default', {})


def _build_all_translations_cache() -> Dict[str, Dict[str, str]]:
    """Build merged translation cache grouped by language based on translation table and default translation.

    Returns:
        Dict[str, Dict[str, str]]: Language code to merged translation mapping cache.
    """

    cache: Dict[str, Dict[str, str]] = {}
    for lang_code, lang_translations in TRANSLATIONS.items():
        merged: Dict[str, str] = dict(DEFAULT_TRANSLATIONS)
        if lang_translations is not DEFAULT_TRANSLATIONS:
            merged.update(lang_translations)
        cache[lang_code] = merged
    return cache


ALL_TRANSLATIONS_CACHE: Dict[str, Dict[str, str]] = _build_all_translations_cache()  # Merged translation cache

# Supported language name mapping table
LANGUAGE_NAMES = {
    'zh-hans': '🇨🇳简体中文',
    'zh-hant': '🇹🇼繁體中文',
    'en': '🇺🇸English',
    'pt': '🇵🇹Português',
    'es': '🇪🇸Español',
    'ja': '🇯🇵日本語',
    'fr': '🇫🇷Français',
    'ru': '🇷🇺Русский',
}


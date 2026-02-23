from . import es, en, pt

DEFAULT_LANG = "es"
SUPPORTED_LANGS = {"es", "en", "pt"}

_MODULE_BY_LANG = {
    "es": es,
    "en": en,
    "pt": pt,
}


def get_language_code(user):
    code = getattr(user, "preferred_lang", DEFAULT_LANG) or DEFAULT_LANG
    return code if code in SUPPORTED_LANGS else DEFAULT_LANG


def get_translation(user, section):
    lang_code = get_language_code(user)
    lang_module = _MODULE_BY_LANG.get(lang_code, _MODULE_BY_LANG[DEFAULT_LANG])
    fallback_module = _MODULE_BY_LANG[DEFAULT_LANG]

    section_dict = getattr(lang_module, section, None) or getattr(fallback_module, section, {})
    base_dict = getattr(lang_module, "base", None) or getattr(fallback_module, "base", {})
    return section_dict, base_dict

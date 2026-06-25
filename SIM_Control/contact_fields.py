import re

PREFERRED_COUNTRIES = (
    ("MX", "México", "+52"),
    ("AR", "Argentina", "+54"),
    ("BO", "Bolivia", "+591"),
    ("BR", "Brasil", "+55"),
    ("CL", "Chile", "+56"),
    ("CO", "Colombia", "+57"),
    ("CR", "Costa Rica", "+506"),
    ("DO", "República Dominicana", "+1"),
    ("EC", "Ecuador", "+593"),
    ("GT", "Guatemala", "+502"),
    ("HN", "Honduras", "+504"),
    ("NI", "Nicaragua", "+505"),
    ("PA", "Panamá", "+507"),
    ("PY", "Paraguay", "+595"),
    ("PE", "Perú", "+51"),
    ("SV", "El Salvador", "+503"),
    ("UY", "Uruguay", "+598"),
    ("VE", "Venezuela", "+58"),
)

COUNTRY_CHOICES = tuple((code, name) for code, name, _dial in PREFERRED_COUNTRIES)
COUNTRY_DIAL_CODES = {code: dial for code, _name, dial in PREFERRED_COUNTRIES}
COUNTRY_NAMES = {code: name for code, name, _dial in PREFERRED_COUNTRIES}
COUNTRY_CODES_BY_NAME = {name.lower(): code for code, name, _dial in PREFERRED_COUNTRIES}


def normalize_country(value):
    value = (value or "").strip()
    if not value:
        return ""
    upper_value = value.upper()
    if upper_value in COUNTRY_DIAL_CODES:
        return upper_value
    return COUNTRY_CODES_BY_NAME.get(value.lower(), value)


def dial_for_country(country):
    return COUNTRY_DIAL_CODES.get(normalize_country(country), "")


def split_phone_number(value, country="MX"):
    value = (value or "").strip()
    country = normalize_country(country) or "MX"
    dial = dial_for_country(country) or "+52"

    for candidate in sorted(COUNTRY_DIAL_CODES.values(), key=len, reverse=True):
        if value.startswith(candidate):
            local = value[len(candidate):].strip()
            return candidate, re.sub(r"\D", "", local)

    return dial, re.sub(r"\D", "", value)


def normalize_phone_number(phone, country):
    country = normalize_country(country)
    dial = dial_for_country(country)
    digits = re.sub(r"\D", "", phone or "")

    if not country:
        raise ValueError("Selecciona un país.")
    if not dial:
        raise ValueError("El país seleccionado no tiene código telefónico configurado.")
    if not digits:
        raise ValueError("Ingresa un número telefónico.")
    if len(digits) < 7 or len(digits) > 15:
        raise ValueError("El número telefónico debe tener entre 7 y 15 dígitos.")

    return f"{dial} {digits}"

LABELS = [
    "Procedural arguments—Non contestation by the parties",
    "Method of interpretation—Textual interpretation",
    "Method of interpretation—Historical interpretation",
    "Method of interpretation—Systematic interpretation",
    "Method of interpretation—Teleological interpretation",
    "Method of interpretation—Comparative law",
    "Test of the principle of proportionality—Legal basis",
    "Test of the principle of proportionality—Legitimate purpose",
    "Test of the principle of proportionality—Suitability",
    "Test of the principle of proportionality—Necessity/Proportionality",
    "Institutional arguments—Overruling",
    "Institutional arguments—Distinguishing",
    "Institutional arguments—Margin of Appreciation",
    "Precedents of the ECHR",
    "Decision of the ECHR",
    "Application to the concrete case",
]
LABEL_ALIASES = {label.casefold(): label for label in LABELS}
def canonical_label(value):
    if value is None: return None
    return LABEL_ALIASES.get(" ".join(str(value).replace("–", "—").split()).casefold())

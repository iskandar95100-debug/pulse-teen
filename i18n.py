"""Interface text. Add a new language by adding another dict and setting LANG."""
LANG = "en"
TEXT = {
    "en": {
        "home": "Home", "plan": "My plan", "life": "Lifestyle", "moti": "Motivation",
        "profile": "Profile", "login": "Log in", "logout": "Log out", "signup": "Sign up",
        "start": "Get Started",
        "disclaimer": "PulseTeen offers general fitness guidance, not medical advice. "
                      "Please consult a doctor before starting if you have a health condition, "
                      "injury or concern, and stop if you feel pain, dizziness or unwell.",
    }
}

def t(key):
    return TEXT.get(LANG, TEXT["en"]).get(key) or TEXT["en"].get(key, key)

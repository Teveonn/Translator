import cv2
import mss
import numpy as np
import pytesseract
import argostranslate.package as pkg
import argostranslate.translate as tr

# ---------------------------------------------------------------- config
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DEBUG = True                    # saves debug.png so you can see what OCR sees
PSM = 6                         # 6 = one block of text, 7 = one line, 3 = full page layout
REGION = {"left": 0, "top": 100, "width": 800, "height": 600}
DEFAULT_SOURCE = "rus"
DEFAULT_TARGET = "eng"

# The single language table. The key is the Tesseract code (what the user types
# now, and what a drop-down will store later). Adding a language is one line.
# "argos" is the two-letter code Argos Translate uses.
LANGUAGES = {
    "eng": {"name": "English", "argos": "en"},
    "rus": {"name": "Russian", "argos": "ru"},
    # "fra": {"name": "French", "argos": "fr"},
}


# ---------------------------------------------------------------- language choices
def available_languages():
    """Languages that are in LANGUAGES AND have Tesseract data installed.

    These are the valid *source* languages (the ones OCR can read). Use this
    list to fill the source drop-down later.
    """
    installed = set(pytesseract.get_languages(config=""))
    return [code for code in LANGUAGES if code in installed]


def ask_language(prompt, default, options):
    """Ask on the command line until the user types a valid code."""
    while True:
        code = input(f"{prompt} [{default}]: ").strip().lower() or default
        if code in options:
            return code
        print(f"  '{code}' isn't available. Choose from: {', '.join(options)}")


# ---------------------------------------------------------------- stage 1: capture
def capture(region):
    with mss.MSS() as sct:
        shot = sct.grab(region)
        return np.array(shot)[:, :, :3]  # drop alpha, keep BGR


# ---------------------------------------------------------------- stage 2: preprocess
def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() < 127:  # mostly dark = dark mode, so invert
        bw = cv2.bitwise_not(bw)
    return bw


# ---------------------------------------------------------------- stage 3: OCR
def read_text(img, lang):
    """`lang` is a Tesseract code such as "rus". Loading ONE language model
    (instead of eng+rus together) is both faster and more accurate."""
    return pytesseract.image_to_string(img, lang=lang, config=f"--psm {PSM}").strip()


# ---------------------------------------------------------------- stage 4: translate
def ensure_model(src, tgt):
    """Install the Argos model for src->tgt (two-letter codes) if missing. True if usable."""
    installed = tr.get_installed_languages()
    src_lang = next((l for l in installed if l.code == src), None)
    if src_lang and any(t.to_lang.code == tgt for t in src_lang.translations_from):
        return True

    pkg.update_package_index()
    match = next(
        (p for p in pkg.get_available_packages()
         if p.from_code == src and p.to_code == tgt),
        None,
    )
    if match is None:
        return False
    pkg.install_from_path(match.download())
    return True


def translate(text, src, tgt):
    """Returns the translation, or None if no model exists for this pair."""
    if not ensure_model(src, tgt):
        return None
    return tr.translate(text, src, tgt)


# ---------------------------------------------------------------- pipeline
def run(source, target, region=REGION):
    """source/target are Tesseract codes from LANGUAGES, e.g. "rus", "eng"."""
    img = preprocess(capture(region))
    if DEBUG:
        cv2.imwrite("debug.png", img)

    text = read_text(img, source)
    result = {"text": text, "source": source, "target": target, "translation": None}

    if not text:
        result["status"] = "no_text"
    elif source == target:
        result["status"] = "same_language"
        result["translation"] = text
    else:
        translation = translate(text, LANGUAGES[source]["argos"], LANGUAGES[target]["argos"])
        result["translation"] = translation
        result["status"] = "ok" if translation is not None else "no_model"

    return result


MESSAGES = {
    "no_text": "No text found in the region.",
    "same_language": "Source and target are the same language.",
    "no_model": "No translation model is available for that language pair.",
}

if __name__ == "__main__":
    sources = available_languages()
    targets = list(LANGUAGES)
    print("Source languages (installed in Tesseract):", ", ".join(sources))
    print("Target languages:", ", ".join(targets))

    source = ask_language("Source language", DEFAULT_SOURCE, sources)
    target = ask_language("Target language", DEFAULT_TARGET, targets)

    result = run(source, target)
    print(MESSAGES.get(result["status"], ""))
    print("Original:   ", result["text"])
    print("Translation:", result["translation"])
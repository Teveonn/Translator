import mss, numpy as np
import cv2
import pytesseract
from lingua import LanguageDetectorBuilder
import argostranslate.package as pkg
import argostranslate.translate as tr

DEBUG = True   # set to False to stop writing debug.png

# hardcode region for now
REGION = {"left": 0, "top": 100, "width": 800, "height": 600}

# hardcode a target language to translate to for now
TARGET_LANG = "en"

# below this confidence the detected language is treated as unreliable
MIN_CONFIDENCE = 0.5

# set tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from lingua import Language, LanguageDetectorBuilder

# One place to add a language: ISO 639-1 code -> (lingua enum, tesseract code).
# Only list languages that appeared in --list-langs.
LANGUAGES = {
    "en": (Language.ENGLISH, "eng"),
    "ru": (Language.RUSSIAN, "rus"),
    # "fr": (Language.FRENCH, "fra"),   # uncomment once fra is installed
}
TESSERACT_LANGS = "+".join(tess for _, tess in LANGUAGES.values())

# prebuild the language detector to save time for repeated translations
detector = LanguageDetectorBuilder.from_languages(
    *[lingua_lang for lingua_lang, _ in LANGUAGES.values()]
).build()


# OCR
def capture(region):
    with mss.MSS() as sct:
        shot = sct.grab(region)
        return np.array(shot)[:, :, :3]   # drop the alpha channel, keep BGR

# Image processing for clearer text
def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() < 127:            # mostly dark → dark-mode, so invert
        bw = cv2.bitwise_not(bw)
    return bw

# read the text from the image, pass installed alphabets / languages in 
def read_text(img, langs=TESSERACT_LANGS):
    return pytesseract.image_to_string(img, lang=langs, config="--psm 6").strip()

# detect the language of the text
def detect(text):
    lang = detector.detect_language_of(text)
    if lang is None:
        return None, 0.0
    conf = detector.compute_language_confidence(text, lang)
    return lang.iso_code_639_1.name.lower(), conf   # e.g. ("fr", 0.98)


def ensure_model(src, tgt):
    installed = tr.get_installed_languages()
    src_lang = next((l for l in installed if l.code == src), None)
    if src_lang and any(t.to_lang.code == tgt for t in src_lang.translations_from):
        return True                      # already installed

    pkg.update_package_index()
    match = next((p for p in pkg.get_available_packages()
                  if p.from_code == src and p.to_code == tgt), None)
    if match is None:
        return False                     # no direct model for this pair
    pkg.install_from_path(match.download())
    return True

# returns the translation, or None if no model exists for this language pair
def translate(text, src, tgt):
    if not ensure_model(src, tgt):
        return None
    return tr.translate(text, src, tgt)


def run(region=REGION, target=TARGET_LANG):
    img = preprocess(capture(region))
    if DEBUG:
        cv2.imwrite("debug.png", img)

    text = read_text(img)
    if not text:
        return {"status": "no_text", "text": "", "src": None,
                "conf": 0.0, "translation": None}

    src, conf = detect(text)
    result = {"text": text, "src": src, "conf": conf, "translation": None}

    if src is None:
        result["status"] = "undetected"
    elif conf < MIN_CONFIDENCE:
        result["status"] = "low_confidence"
    elif src == target:
        result["status"] = "same_language"
        result["translation"] = text
    else:
        translation = translate(text, src, target)
        result["translation"] = translation
        result["status"] = "ok" if translation is not None else "no_model"

    return result

if __name__ == "__main__":
    result = run()
    print(result["status"], result["src"], f'{result["conf"]:.0%}')
    print(result["text"])
    print(result["translation"])
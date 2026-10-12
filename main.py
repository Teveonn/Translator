import mss, numpy as np
import cv2
import pytesseract
from lingua import LanguageDetectorBuilder
import argostranslate.package as pkg
import argostranslate.translate as tr

# prebuild the language detector to save time for repeated translations
detector = LanguageDetectorBuilder.from_all_languages().build()

# set tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# hardcode a target language to translate to for now
target_language = "en"

# 3 letter to ISO language dictionary
lang_dictionary = {"en": "eng", "ru": "rus", "fr": "fra"} 

# hardcode region for now
region = {"left": 0, "top": 100, "width": 800, "height": 600}

available_alphabets = ["eng", "rus"]
available_alphabets_string = "+".join(available_alphabets)
print(available_alphabets_string)

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

# function to attempt to crop image to text region for more accurate reading // not needed currently
"""def crop_to_text(bw, pad=20):
    ys, xs = np.where(bw < 128)          # dark pixels = ink
    if len(xs) == 0:
        return bw
    crop = bw[ys.min():ys.max()+1, xs.min():xs.max()+1]
    return cv2.copyMakeBorder(crop, pad, pad, pad, pad,
                              cv2.BORDER_CONSTANT, value=255)
"""
# read the text from the image, pass installed alphabets / languages in 
def read_text(img, langs):
    
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

def translate(text, src, tgt):
    if not ensure_model(src, tgt):
        return f"[No {src}->{tgt} model available]"
    return tr.translate(text, src, tgt)




img = capture(region)
img = preprocess(img)
#img = crop_to_text(img)
cv2.imwrite("debug.png", img)
text = read_text(img, available_alphabets_string)
print(text)
lang = detect(read_text(img, available_alphabets_string))
print(lang)
ensure_model(lang[0], target_language)
print(translate(text, lang[0], target_language))
import mss, numpy as np
import cv2
import pytesseract
from lingua import LanguageDetectorBuilder
import argostranslate.package as pkg
import argostranslate.translate as tr

detector = LanguageDetectorBuilder.from_all_languages().build()
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def capture(region):
    # region = {"left": 100, "top": 200, "width": 600, "height": 300}
    with mss.MSS() as sct:
        shot = sct.grab(region)
        return np.array(shot)[:, :, :3]   # drop the alpha channel, keep BGR


def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() < 127:            # mostly dark → dark-mode, so invert
        bw = cv2.bitwise_not(bw)
    return bw

"""def crop_to_text(bw, pad=20):
    ys, xs = np.where(bw < 128)          # dark pixels = ink
    if len(xs) == 0:
        return bw
    crop = bw[ys.min():ys.max()+1, xs.min():xs.max()+1]
    return cv2.copyMakeBorder(crop, pad, pad, pad, pad,
                              cv2.BORDER_CONSTANT, value=255)
"""
def read_text(img, langs="eng+rus"):
    return pytesseract.image_to_string(img, lang=langs, config="--psm 6").strip()


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



# hardcode region
region = {"left": 0, "top": 100, "width": 800, "height": 600}
img = capture(region)
img = preprocess(img)
#img = crop_to_text(img)
cv2.imwrite("debug.png", img)
text = read_text(img)
print(text)
lang = detect(read_text(img))
print(lang)
ensure_model(lang[0], "eng")
print(translate(text, lang[0], "eng"))
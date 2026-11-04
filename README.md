# Screen Translator

Read text from a region of your screen using OCR, then translate it into another language, entirely offline.

> **Status:** early prototype. The core pipeline works from the command line on a fixed screen region. A region selector, drop-down language pickers, a hotkey and a result overlay are planned (see the [roadmap](#roadmap)).

## How it works

```
Capture region  →  Preprocess  →  OCR  →  Translate
    (mss)          (OpenCV)    (Tesseract)  (Argos Translate)
```

| Stage | What it does | Library |
|---|---|---|
| Capture | Grabs the pixels of a rectangular screen region | `mss` |
| Preprocess | Converts to greyscale, upscales 2x, applies Otsu thresholding, and inverts dark-mode text so it is dark on light | `opencv-python`, `numpy` |
| OCR | Reads the text using the language you selected | `pytesseract` (wraps Tesseract) |
| Translate | Translates the text with an offline neural model, downloading the model for the language pair on first use | `argostranslate` |

Each stage is a separate function (image in, text out, and so on), so any one can be swapped for something else without touching the rest.

## Language selection

The app does **not** detect the source language automatically. You choose the source and target language yourself. This keeps OCR fast and accurate, because Tesseract loads a single language model instead of guessing between several.

Languages are identified by their Tesseract codes (`eng`, `rus`, ...). A single table in `main.py` maps each code to a display name and the two-letter code that Argos Translate uses:

```python
LANGUAGES = {
    "eng": {"name": "English", "argos": "en"},
    "rus": {"name": "Russian", "argos": "ru"},
}
```

## Requirements

- Windows (developed and tested on Windows with PowerShell)
- Python 3.11 or newer. If a dependency fails to build on a very new Python release, use 3.11 or 3.12.
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) with the language data you need
- An internet connection the first time you translate a given language pair (to download the Argos model)

## Installation

1. **Clone the repository and create a virtual environment.**

   ```powershell
   git clone <your-repo-url>
   cd Translator
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks the activation script, allow scripts for your user account and try again:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```

2. **Install the Python packages.**

   ```powershell
   pip install -r requirements.txt
   ```

   `requirements.txt` lists the direct dependencies. `mss` has a minimum version because `main.py` uses the `mss.MSS` class, which was added in 10.2.0. `argostranslate` pulls in large machine-learning dependencies, so the install can take a few minutes.

3. **Install Tesseract.**

   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```

   You can also use the installer from the UB Mannheim page. During setup, expand **Additional language data** and tick every language you want to read (for example Russian).

4. **Check which languages Tesseract has.**

   ```powershell
   & "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
   ```

   If a language is missing, re-run the installer and tick it, or download its `.traineddata` file into `C:\Program Files\Tesseract-OCR\tessdata`.

5. **Point the app at Tesseract.** `main.py` sets this near the top. Change it if you installed Tesseract somewhere else:

   ```python
   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

## Usage

1. Put the text you want to translate on screen, inside the region defined by `REGION` in `main.py`. The default is a 800x600 area starting at `left=0, top=100`.
2. Run:

   ```powershell
   python main.py
   ```

3. Enter a source and target language when asked. Press Enter to accept the default shown in brackets.

   ```
   Source languages (installed in Tesseract): eng, rus
   Target languages: eng, rus
   Source language [rus]:
   Target language [eng]:
   ```

4. The program prints the recognised text and its translation.

The first translation for a language pair downloads its model and can take a while. Later runs reuse the installed model.

## Configuration

All settings are constants near the top of `main.py`.

| Setting | Purpose |
|---|---|
| `REGION` | The screen rectangle to capture, in pixels: `left`, `top`, `width`, `height` |
| `DEFAULT_SOURCE`, `DEFAULT_TARGET` | Languages offered when you just press Enter |
| `LANGUAGES` | The supported languages (see above) |
| `PSM` | Tesseract page segmentation mode: `6` for one block of text, `7` for a single line, `3` for full page layout |
| `DEBUG` | When `True`, saves the preprocessed image to `debug.png` so you can see exactly what OCR received |

### Adding a language

1. Install its Tesseract data and confirm it appears in `tesseract --list-langs`.
2. Add one line to `LANGUAGES`, for example:

   ```python
   "fra": {"name": "French", "argos": "fr"},
   ```

## Project structure

```
Translator/
├── main.py             # the whole pipeline: capture, preprocess, OCR, translate, command-line entry point
├── requirements.txt    # Python dependencies
├── README.md
└── .venv/         # virtual environment (not committed)
```

Add `.venv/`, `__pycache__/` and `debug.png` to `.gitignore`.

## Known limitations

- **The capture region is hardcoded.** Edit `REGION` until the region selector exists.
- **One source language at a time.** A page with mixed languages, such as Russian text containing English words, will read the secondary language poorly.
- **Simple thresholding.** Otsu thresholding works well for plain text but can struggle with busy backgrounds, gradients and images.
- **Direct model pairs only.** The app installs a model only if Argos publishes one for that exact pair. If it does not, the result status is `no_model`.
- **Poor test input.** A long run of identical touching characters (such as a line of "g") is unreliable for Tesseract even with a good image. Test with real sentences.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `TesseractNotFoundError` | Tesseract is not installed or `tesseract_cmd` points to the wrong path. Check the path with `Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"`. |
| `Failed loading language 'rus'` | The language data is not installed. Re-run the Tesseract installer and tick the language, or add the `.traineddata` file to the `tessdata` folder. |
| Garbled or empty OCR output | Open `debug.png` and look at what Tesseract received. Check the region covers the text with a margin, the text is large enough, and the image is not cut off at the edges. |
| Translation crashes or returns nothing | Make sure you are using the two-letter Argos code via the `LANGUAGES` table (`en`, not `eng`), and that you were online for the first download of that pair. |
| `DeprecationWarning: mss.mss is deprecated` | Use `mss.MSS()` instead of `mss.mss()`. The code in this repository already does. |
| `AttributeError: module 'mss' has no attribute 'MSS'` | Your `mss` is older than 10.2.0. Run `pip install -U -r requirements.txt`. |
| `&&` is not a valid statement separator | Windows PowerShell 5.1 does not support `&&`. Run the commands on separate lines or chain them with `;`. |

## Roadmap

- [x] Capture, preprocess, OCR and translate on a fixed region
- [x] Offline translation with automatic model download
- [x] User-selected source and target language (typed Tesseract codes)
- [ ] Drag-to-select region selector (with Windows DPI scaling handled so coordinates match what `mss` captures)
- [ ] Drop-down language pickers
- [ ] Global hotkey and an always-on-top result overlay, with the pipeline running in a background thread
- [ ] Live mode: re-run only when the captured pixels change, and cache translations
- [ ] Labelled test set and a character-error-rate evaluation script to measure preprocessing changes
- [ ] Optional text-to-speech for the translation
- [ ] Packaging as a standalone Windows executable

## Built with

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and [pytesseract](https://github.com/madmaze/pytesseract)
- [Argos Translate](https://github.com/argosopentech/argos-translate)
- [mss](https://github.com/BoboTiG/python-mss)
- [OpenCV](https://opencv.org/) and [NumPy](https://numpy.org/)

## License

Add a license before publishing the repository (MIT is a common choice for small projects).
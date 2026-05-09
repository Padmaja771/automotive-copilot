"""
Download Real Public Vehicle Manuals
======================================
Downloads freely available automotive PDFs from public government and
manufacturer sources that are in the public domain or openly licensed.

Sources used:
  - NHTSA (National Highway Traffic Safety Administration) — public domain
  - EPA fuel economy data — public domain
  - Our locally generated synthetic manuals (always available)

Run:  python data/download_real_manuals.py
"""

import os
import urllib.request
import urllib.error

MANUALS_DIR = os.path.join(os.path.dirname(__file__), "raw_manuals")
os.makedirs(MANUALS_DIR, exist_ok=True)

# ── Public Domain PDFs ────────────────────────────────────────────────────────
# These are genuine public government automotive documents
PUBLIC_MANUALS = [
    {
        "filename": "nhtsa_obd2_diagnostic_guide.pdf",
        "url": "https://www.nhtsa.gov/sites/nhtsa.gov/files/2022-09/obd-ii-overview.pdf",
        "description": "NHTSA OBD-II Diagnostic Overview — public domain",
        "fallback": True,
    },
    {
        "filename": "epa_vehicle_emissions_guide.pdf",
        "url": "https://www.epa.gov/sites/default/files/2016-02/documents/420b16016.pdf",
        "description": "EPA Vehicle Emissions & OBD Guide — public domain",
        "fallback": True,
    },
    {
        "filename": "nhtsa_adas_safety_report.pdf",
        "url": "https://www.nhtsa.gov/sites/nhtsa.gov/files/2022-09/ADAS-Primer.pdf",
        "description": "NHTSA ADAS Systems Primer — public domain",
        "fallback": True,
    },
]


def download_pdf(url: str, dest_path: str, description: str) -> bool:
    """Attempts to download a PDF. Returns True on success."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AutomotiveCopilot/1.0; Research)"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if len(content) < 1000:
                print(f"  ⚠️  Response too small, likely not a PDF: {url}")
                return False
            with open(dest_path, "wb") as f:
                f.write(content)
            size_kb = len(content) // 1024
            print(f"  ✅ {os.path.basename(dest_path)} ({size_kb} KB) — {description}")
            return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ⚠️  Download failed ({type(e).__name__}): {os.path.basename(dest_path)}")
        return False


def list_available_manuals():
    """Shows all PDFs currently in raw_manuals/."""
    files = [f for f in os.listdir(MANUALS_DIR) if f.endswith(".pdf")]
    print(f"\n{'='*55}")
    print(f"  Vehicle Manuals in data/raw_manuals/ ({len(files)} files)")
    print(f"{'='*55}")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(MANUALS_DIR, f)) // 1024
        print(f"  {f:<45} {size:>5} KB")
    print(f"{'='*55}")
    return files


if __name__ == "__main__":
    print("Downloading public automotive reference documents...\n")
    downloaded = 0
    skipped = 0

    for manual in PUBLIC_MANUALS:
        dest = os.path.join(MANUALS_DIR, manual["filename"])
        if os.path.exists(dest):
            size = os.path.getsize(dest) // 1024
            print(f"  ✓  Already exists: {manual['filename']} ({size} KB)")
            skipped += 1
            continue
        success = download_pdf(manual["url"], dest, manual["description"])
        if success:
            downloaded += 1

    synthetic = [f for f in os.listdir(MANUALS_DIR) if f.endswith(".pdf")]
    print(f"\nSummary: {downloaded} downloaded, {skipped} already cached")
    print(f"Total PDFs available for upload: {len(synthetic)}")
    list_available_manuals()

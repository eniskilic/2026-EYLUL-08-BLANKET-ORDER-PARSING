import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch, landscape
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

# Optional OCR stack — used only as a fallback for image/photo shipping labels
# that have no extractable text layer. The app runs fine without it (text-based
# labels still work); OCR just extends matching to scanned labels.
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# --------------------------------------
# Page Configuration
# --------------------------------------
st.set_page_config(
    page_title="Blanket Order Manager",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------
# Dark Mode Custom CSS Styling
# --------------------------------------
st.markdown("""
<style>
    /* ---------- Light, airy theme · terracotta accent ---------- */
    :root {
        --bg: #faf9f6;
        --surface: #ffffff;
        --surface-soft: #f5f3ee;
        --border: #e9e6df;
        --border-soft: #f0ede7;
        --text: #26251f;
        --text-soft: #6b6960;
        --text-muted: #9a978d;
        --accent: #b5623c;
        --accent-dark: #8a4426;
        --accent-soft: #f6ede8;
    }

    .stApp { background: var(--bg); }
    .main .block-container { padding-top: 2rem; max-width: 1200px; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; }

    /* Sidebar radio as nav */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        display: flex; align-items: center;
        padding: 10px 12px; margin: 2px 0;
        border-radius: 10px; cursor: pointer;
        font-size: 14px; transition: background .15s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: var(--surface-soft); }

    /* Headings */
    h1 { color: var(--text); font-weight: 600; font-size: 1.9rem; }
    h2 { color: var(--text); font-weight: 600; font-size: 1.35rem; margin-top: 0.5rem; }
    h3 { color: var(--text); font-weight: 600; font-size: 1.1rem; }
    p, span, div, label, li { color: var(--text); }

    /* Metric tiles */
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        padding: 18px 18px;
        border-radius: 14px;
    }
    [data-testid="stMetric"]:hover { border-color: var(--accent); transition: border-color .2s ease; }
    [data-testid="stMetric"] label {
        font-size: 0.72rem !important; color: var(--text-muted) !important;
        font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 2rem !important; font-weight: 600 !important; color: var(--text) !important;
    }

    /* Buttons */
    .stButton button {
        background: var(--accent); color: #ffffff; border: none;
        border-radius: 10px; padding: 11px 20px; font-weight: 600; width: 100%;
        transition: background .18s ease, transform .1s ease;
    }
    .stButton button:hover { background: var(--accent-dark); transform: translateY(-1px); }

    .stDownloadButton button {
        background: var(--surface); color: var(--accent-dark);
        border: 1px solid var(--accent); border-radius: 10px;
        padding: 10px 18px; font-weight: 600; width: 100%;
    }
    .stDownloadButton button:hover { background: var(--accent-soft); }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: var(--surface); padding: 28px;
        border-radius: 14px; border: 1.5px dashed var(--border);
    }
    [data-testid="stFileUploader"]:hover { border-color: var(--accent); background: var(--accent-soft); }

    /* Alerts */
    .stAlert {
        background: var(--surface-soft) !important;
        border: 1px solid var(--border) !important;
        border-left: 4px solid var(--accent) !important;
        border-radius: 10px; color: var(--text) !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border-radius: 12px; border: 1px solid var(--border); overflow: hidden; }

    /* Expander */
    [data-testid="stExpander"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important; border-radius: 12px;
    }

    /* Tabs (if any remain) — light */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 6px; background: var(--surface-soft);
        padding: 5px; border-radius: 12px; border: 1px solid var(--border);
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        height: 40px; padding: 0 16px; border-radius: 9px;
        color: var(--text-soft); font-weight: 600; background: transparent;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: var(--accent) !important; color: #ffffff !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    [data-testid="stTabs"] [data-baseweb="tab-border"] { background: transparent !important; }

    hr { border: none; border-top: 1px solid var(--border); margin: 1.6rem 0; }
    .stProgress > div > div { background: var(--accent); }
    .stSpinner > div { border-top-color: var(--accent) !important; }

    /* Status pill */
    .status-indicator {
        display: inline-flex; align-items: center; gap: 8px;
        background: var(--accent-soft); color: var(--accent-dark);
        padding: 6px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;
    }
    .status-dot {
        width: 8px; height: 8px; background: var(--accent);
        border-radius: 50%; animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* Metric card container tiles used in custom sections */
    .tile {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 14px; padding: 16px 18px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------
# Color dictionary for Spanish translation
# --------------------------------------
COLOR_TRANSLATIONS = {
    "white": "Blanco",
    "black": "Negro",
    "brown": "Marrón",
    "blue": "Azul",
    "navy": "Azul Marino",
    "red": "Rojo",
    "pink": "Rosa",
    "light pink": "Rosa Claro",
    "hot pink": "Rosa Fucsia",
    "salmon pink": "Rosa Salmón",
    "purple": "Morado",
    "lilac": "Lila",
    "gray": "Gris",
    "grey": "Gris",
    "gold": "Dorado",
    "silver": "Plateado",
    "beige": "Beige",
    "green": "Verde",
    "olive": "Verde Oliva",
    "yellow": "Amarillo",
    "champagne": "Champán"
}

# --------------------------------------
# Helper Functions
# --------------------------------------
def normalize_zip_wrap(s):
    """
    Repair ZIP+4 codes that were split by a line wrap in the PDF text, e.g.
    '37880-\n2512', '37880- 2512', or '37880-2 512' all become '37880-2512'.
    Amazon packing slips wrap the ZIP across lines for long city/state lines,
    which otherwise strips the +4 and weakens address matching.
    """
    if not s:
        return s
    s = re.sub(r"(\d{5})-\s*(\d)\s*(\d{3})\b", r"\1-\2\3", s)   # 37880-2 512 -> 37880-2512
    s = re.sub(r"(\d{5})-\s+(\d{4})\b", r"\1-\2", s)            # 37880- 2512 -> 37880-2512
    s = re.sub(r"(\d{5})-\s*\n\s*(\d{4})\b", r"\1-\2", s)       # 37880-\n2512 -> 37880-2512
    return s


def extract_zip(text):
    """
    Extract (zip5, zip4) from an address, robust to shipping-label noise.

    Priority:
      1) STATE + ZIP  (e.g. 'AZ 85281', 'TN 37880-2512') — anchors on the real
         ZIP and ignores billing/reference numbers like FedEx 'CAD: 261377523'.
      2) A standalone ZIP+4 anywhere.
      3) A 5-digit number not embedded in a longer digit run (avoids matching
         the first 5 digits of a long reference number).
    """
    if not text:
        return "", ""
    text = normalize_zip_wrap(text)
    m = re.search(r"\b([A-Z]{2})\s+(\d{5})(?:-(\d{4}))?\b", text)
    if m:
        return m.group(2), (m.group(3) or "")
    m = re.search(r"\b(\d{5})-(\d{4})\b", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"(?<!\d)(\d{5})(?!\d)", text)
    if m:
        return m.group(1), ""
    return "", ""


def clean_text(s: str) -> str:
    """Cleans unwanted symbols and color codes."""
    if not s:
        return ""
    s = re.sub(r"\(#?[A-Fa-f0-9]{3,6}\)", "", s)
    s = re.sub(r"■|Seller Name|Your Orders|Returning your item:", "", s)
    s = re.sub(r"\(Most popular\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()

def translate_thread_color(color):
    """Adds Spanish translation."""
    if not color:
        return color
    base = color.strip()
    for eng, esp in COLOR_TRANSLATIONS.items():
        if eng.lower() in base.lower():
            return f"{base} ({esp})"
    return base

def get_bobbin_color(thread_color):
    """Determine bobbin color based on thread color"""
    thread_lower = thread_color.lower()
    if 'navy' in thread_lower or 'black' in thread_lower or 'negro' in thread_lower:
        return 'Black Bobbin'
    else:
        return 'White Bobbin'

def draw_checkbox(canvas_obj, x, y, size, is_checked):
    """Draw a checkbox at position (x, y) with given size."""
    canvas_obj.saveState()
    
    if is_checked:
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setLineWidth(2)
        canvas_obj.rect(x, y, size, size, stroke=1, fill=1)
    else:
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.setLineWidth(2)
        canvas_obj.rect(x, y, size, size, stroke=1, fill=0)
    
    canvas_obj.restoreState()

# --------------------------------------
# Shipping-label reading + address matching
# --------------------------------------
def _read_label_page_text(page, page_index, shipping_pdf_bytes):
    """
    Return the text of one shipping-label page.
    Tries the PDF text layer first (clean digital labels); falls back to OCR
    only when the page has essentially no text (photo/scanned labels).
    """
    text = ""
    try:
        text = page.extract_text() or ""
    except Exception:
        text = ""

    # If the text layer is basically empty, this is likely an image label -> OCR
    if len(text.strip()) < 15 and OCR_AVAILABLE:
        try:
            shipping_pdf_bytes.seek(0)
            images = convert_from_bytes(
                shipping_pdf_bytes.read(),
                first_page=page_index + 1,
                last_page=page_index + 1,
                dpi=300
            )
            if images:
                text = pytesseract.image_to_string(images[0])
        except Exception:
            pass  # OCR failed; leave text as-is (will just fail to match -> warning)

    return text


def extract_label_keys(text):
    """
    Pull matching keys from a shipping-label's text: ZIP+4, 5-digit ZIP,
    street number, and normalized name tokens.

    IMPORTANT: shipping labels print the SENDER address (Fairfield, NJ 07004)
    above the recipient. We must read from the SHIP-TO portion only, otherwise
    we'd match on the sender's ZIP. We locate a "ship to"/"deliver to" marker
    and parse only the text after it; if no marker is found we drop a known
    sender block, then fall back to the whole text.
    """
    keys = {"zip5": "", "zip4": "", "street_no": "", "name_tokens": set(), "raw": text}
    if not text:
        return keys

    work = text
    # Prefer text after a ship-to / deliver-to marker. FedEx labels use a bare
    # "TO" (not "SHIP TO"), so we accept that too — anchored to line start so we
    # don't trip on the word "to" mid-address.
    marker = re.search(r"(ship\s*to|deliver\s*to|^\s*to\b)\s*:?", text, re.IGNORECASE | re.MULTILINE)
    if marker:
        work = text[marker.end():]
    else:
        # No marker — strip the known sender block if present
        work = re.sub(r"[\s\S]*?FAIRFIELD[^\n]*07004[^\n]*", "", text, count=1, flags=re.IGNORECASE) or text

    # ZIP via the robust extractor (state-anchored; ignores FedEx ref numbers
    # like 'CAD: 261377523' that previously misread as a ZIP).
    keys["zip5"], keys["zip4"] = extract_zip(work)

    street_m = re.search(r"\b(\d{1,6})\b", normalize_zip_wrap(work))
    if street_m:
        keys["street_no"] = street_m.group(1)

    # name tokens: alphabetic words >= 3 chars, minus common label noise
    stop = {
        "ship", "the", "and", "apt", "ave", "street", "road", "lane", "drive",
        "unit", "suite", "ste", "blvd", "usps", "ups", "fedex", "ground",
        "tracking", "postage", "paid", "from", "mailed", "advantage", "select",
        "parcel", "carrier", "response", "leave", "deliver", "fairfield",
        "gloria", "new", "jersey", "saver", "family", "floor", "circle", "court",
    }
    for w in re.findall(r"[A-Za-z]{3,}", work.lower()):
        if w not in stop:
            keys["name_tokens"].add(w)
    return keys


def match_label_to_order(label_keys, orders, used_order_ids):
    """
    Given one label's keys and the list of order dicts, return the index of the
    best unmatched order, plus a confidence string. None if no confident match.

    Priority: ZIP+4  ->  5-digit ZIP + street number  ->  ZIP + name tokens.
    """
    lz5, lz4 = label_keys["zip5"], label_keys["zip4"]
    lstreet = label_keys["street_no"]
    ltokens = label_keys["name_tokens"]

    if not lz5:
        return None, "no-zip"

    # candidates: unused orders sharing the 5-digit ZIP
    candidates = [
        i for i, o in enumerate(orders)
        if o["Ship ZIP"] == lz5 and o["Order ID"] not in used_order_ids
    ]
    if not candidates:
        return None, "no-zip-match"

    # 1) unique ZIP+4 match
    if lz4:
        z4 = [i for i in candidates if orders[i]["Ship ZIP4"] and orders[i]["Ship ZIP4"] == lz4]
        if len(z4) == 1:
            return z4[0], "zip4"
        if len(z4) > 1:
            candidates = z4  # narrow, then fall through to tiebreakers

    # 2) single candidate on the 5-digit ZIP alone
    if len(candidates) == 1:
        return candidates[0], "zip5-unique"

    # 3) tiebreak by street number
    if lstreet:
        st_match = [i for i in candidates if orders[i]["Ship Street No"] == lstreet]
        if len(st_match) == 1:
            return st_match[0], "zip+street"
        if len(st_match) > 1:
            candidates = st_match

    # 4) tiebreak by name-token overlap — but strip geography words (city/state/
    #    street types) so we don't false-match on a shared city like "brooklyn".
    #    Require a clear single winner; if the top two tie, flag instead of guess.
    GEO = {
        "brooklyn", "york", "boston", "chicago", "miami", "portland", "newport",
        "philadelphia", "hartsdale", "oneonta", "acushnet", "racine", "tarzana",
        "sandusky", "middletown", "phoenixville", "littleton", "milford", "drums",
        "west", "end", "north", "south", "east", "saint", "petersburg", "san",
        "jose", "charlotte", "avenue", "road", "lane", "drive", "street", "blvd",
        "circle", "court", "way", "place", "apt", "unit", "suite", "ste",
        "hwy", "highway", "rd", "ave", "ln", "dr", "ct", "cir", "pkwy",
    }
    scored = []
    for i in candidates:
        otokens = set(re.findall(r"[A-Za-z]{3,}", orders[i]["Ship To Full"].lower()))
        overlap = (ltokens & otokens) - GEO
        scored.append((len(overlap), i))
    scored.sort(reverse=True)

    if scored:
        top_score, top_i = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else -1
        # need a real name-word overlap AND a strictly better winner than #2
        if top_score >= 1 and top_score > second_score:
            return top_i, f"zip+name({top_score})"

    return None, "ambiguous"


def make_warning_label(order):
    """Generate a single 4x6 warning page for an order with no matched shipping label."""
    buf = BytesIO()
    page_size = landscape((4 * inch, 6 * inch))
    c = canvas.Canvas(buf, pagesize=page_size)
    W, H = page_size

    c.setFillColor(colors.black)
    c.rect(0, H - 0.9 * inch, W, 0.9 * inch, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(W / 2, H - 0.62 * inch, "⚠ NO SHIPPING LABEL")

    c.setFillColor(colors.black)
    y = H - 1.4 * inch
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.4 * inch, y, "This order had no matching shipping label.")
    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.4 * inch, y, "Locate/print the label manually before shipping.")
    y -= 0.45 * inch

    c.setFont("Helvetica", 12)
    for line in [
        f"Order ID: {order.get('Order ID','')}",
        f"Buyer: {order.get('Buyer Name','')}",
        f"Name on blanket: {order.get('Customization Name','')}",
        f"Ship to: {order.get('Ship To Full','')}",
    ]:
        # wrap long ship-to line
        while len(line) > 60:
            c.drawString(0.4 * inch, y, line[:60])
            line = "    " + line[60:]
            y -= 0.24 * inch
        c.drawString(0.4 * inch, y, line)
        y -= 0.28 * inch

    c.setStrokeColor(colors.black)
    c.setLineWidth(3)
    c.rect(0.15 * inch, 0.15 * inch, W - 0.3 * inch, H - 0.3 * inch, stroke=1, fill=0)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def merge_shipping_and_manufacturing_labels(shipping_pdf_bytes, manufacturing_pdf_bytes, order_dataframe):
    """
    Merge shipping + manufacturing labels, matching by shipping ADDRESS
    (ZIP+4 -> ZIP+street -> name tokens), NOT by page position.

    Master sequence = the order-detail order (dataframe order). For each order:
      matched   -> [shipping label] + [manufacturing label(s)]
      unmatched -> [warning label]  + [manufacturing label(s)]
    Leftover shipping labels that matched no order are appended at the end and
    also returned for on-screen reporting.

    Returns: (buffer, n_matched, n_unmatched, unmatched_orders, leftover_labels)
    """
def merge_shipping_and_manufacturing_labels(shipping_pdf_bytes, manufacturing_pdf_bytes, order_dataframe):
    """
    Merge shipping + manufacturing labels by SEQUENCE (position order).

    The shipping labels are assumed to be in the same order as the orders in the
    dataframe: shipping label #1 -> order #1, #2 -> #2, and so on. For each order:
      label available -> [shipping label] + [manufacturing label(s)]
      label missing   -> [warning label]  + [manufacturing label(s)]

    A trailing "successful label purchase" manifest page (text-only) is detected
    and skipped so it isn't consumed as a label. Any leftover shipping labels
    (more labels than orders) are appended at the end for review.

    Returns: (buffer, n_matched, n_unmatched, unmatched_orders, leftover_labels)
    """
    try:
        shipping_pdf = PdfReader(shipping_pdf_bytes)
        manufacturing_pdf = PdfReader(manufacturing_pdf_bytes)

        # ---- build ordered list of unique orders (preserves dataframe order) ----
        orders = []
        seen = set()
        row_positions = {}  # order_id -> list of mfg page indices
        for row_idx, (_, r) in enumerate(order_dataframe.iterrows()):
            oid = r["Order ID"]
            row_positions.setdefault(oid, []).append(row_idx)
            if oid not in seen:
                seen.add(oid)
                orders.append({
                    "Order ID": oid,
                    "Buyer Name": r.get("Buyer Name", ""),
                    "Customization Name": r.get("Customization Name", ""),
                    "Ship To Full": r.get("Ship To Full", ""),
                })

        # ---- identify real label pages, skipping the manifest page ----
        def _is_manifest_page(t):
            if not t:
                return False
            low = t.lower()
            if "successful label purchase" in low or "list of orders" in low:
                return True
            ids = re.findall(r"\d{3}-\d{7}-\d{7}", t)
            words = re.findall(r"[A-Za-z]{3,}", t)
            return len(ids) >= 3 and len(words) < 10

        real_label_pages = []  # shipping page indices that are actual labels
        for pidx, page in enumerate(shipping_pdf.pages):
            txt = _read_label_page_text(page, pidx, shipping_pdf_bytes)
            if not _is_manifest_page(txt):
                real_label_pages.append(pidx)

        # ---- assemble by sequence ----
        output_pdf = PdfWriter()
        n_matched = 0
        unmatched_orders = []

        for i, o in enumerate(orders):
            oid = o["Order ID"]
            mfg_pages = row_positions.get(oid, [])

            if i < len(real_label_pages):
                # sequence pairing: i-th order gets i-th real label
                output_pdf.add_page(shipping_pdf.pages[real_label_pages[i]])
                n_matched += 1
            else:
                # ran out of labels -> warning page (safety)
                warn = make_warning_label(o)
                output_pdf.add_page(PdfReader(warn).pages[0])
                unmatched_orders.append(o)

            for mi in mfg_pages:
                if mi < len(manufacturing_pdf.pages):
                    output_pdf.add_page(manufacturing_pdf.pages[mi])

        # ---- leftover labels (more labels than orders) appended at the end ----
        leftover_labels = real_label_pages[len(orders):] if len(real_label_pages) > len(orders) else []
        if leftover_labels:
            note = BytesIO()
            page_size = landscape((4 * inch, 6 * inch))
            cc = canvas.Canvas(note, pagesize=page_size)
            Wc, Hc = page_size
            cc.setFont("Helvetica-Bold", 18)
            cc.drawCentredString(Wc / 2, Hc / 2 + 0.3 * inch, "EXTRA SHIPPING LABELS")
            cc.setFont("Helvetica", 12)
            cc.drawCentredString(Wc / 2, Hc / 2 - 0.1 * inch,
                                 f"{len(leftover_labels)} more label(s) than orders — review below")
            cc.showPage()
            cc.save()
            note.seek(0)
            output_pdf.add_page(PdfReader(note).pages[0])
            for pidx in leftover_labels:
                output_pdf.add_page(shipping_pdf.pages[pidx])

        output_buffer = BytesIO()
        output_pdf.write(output_buffer)
        output_buffer.seek(0)

        return output_buffer, n_matched, len(unmatched_orders), unmatched_orders, leftover_labels

    except Exception as e:
        st.error(f"Error merging labels: {str(e)}")
        return None, 0, 0, [], []

# --------------------------------------
# PDF Generation Functions
# --------------------------------------
def generate_manufacturing_labels(dataframe):
    buf = BytesIO()
    page_size = landscape((4 * inch, 6 * inch))
    c = canvas.Canvas(buf, pagesize=page_size)
    W, H = page_size
    left = 0.3 * inch
    right = W - 0.3 * inch
    top = H - 0.3 * inch

    for _, row in dataframe.iterrows():
        y = top
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left, y, f"Order ID: {row['Order ID']}")
        c.drawRightString(right, y, f"Qty: {row['Quantity']}")
        y -= 0.25 * inch
        
        c.setFont("Helvetica", 14)
        c.drawString(left, y, f"Buyer: {row['Buyer Name']}")
        c.drawRightString(right, y, f"Date: {row['Order Date']}")
        y -= 0.3 * inch

        box_height = 0.7 * inch
        box_y = y - box_height
        c.setStrokeColor(colors.black)
        c.setLineWidth(2)
        c.rect(left, box_y, right - left, box_height, stroke=1, fill=0)
        
        c.setFont("Helvetica-Bold", 16)
        text_y = box_y + box_height - 0.24 * inch
        c.drawString(left + 0.1 * inch, text_y, f"BLANKET COLOR: {row['Blanket Color'].upper()}")
        
        text_y -= 0.32 * inch
        c.setFont("Helvetica-BoldOblique", 16)
        c.drawString(left + 0.1 * inch, text_y, f"THREAD COLOR: {row['Thread Color']}")
        
        y = box_y - 0.3 * inch

        c.setFont("Helvetica-Bold", 18)
        c.drawString(left, y, f"★ Name: {row['Customization Name']}")
        y -= 0.4 * inch

        frame_width = (right - left - 0.4 * inch) / 3
        frame_height = 1.1 * inch
        frame_y = y - frame_height
        
        c.setLineWidth(2)
        
        beanie_x = left
        c.rect(beanie_x, frame_y, frame_width, frame_height, stroke=1, fill=0)
        
        checkbox_size = 0.25 * inch
        checkbox_x = beanie_x + (frame_width - checkbox_size) / 2
        checkbox_y = frame_y + frame_height - 0.35 * inch
        is_beanie_checked = (row['Include Beanie'] == "YES")
        draw_checkbox(c, checkbox_x, checkbox_y, checkbox_size, is_beanie_checked)
        
        text_x = beanie_x + frame_width / 2
        text_y = frame_y + frame_height - 0.60 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, "BEANIE")
        
        text_y -= 0.25 * inch
        if row['Include Beanie'] == "YES":
            c.setFont("Helvetica-BoldOblique", 14)
        else:
            c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, row['Include Beanie'])
        
        gift_box_x = beanie_x + frame_width + 0.2 * inch
        c.rect(gift_box_x, frame_y, frame_width, frame_height, stroke=1, fill=0)
        
        checkbox_x = gift_box_x + (frame_width - checkbox_size) / 2
        is_gift_box_checked = (row['Gift Box'] == "YES")
        draw_checkbox(c, checkbox_x, checkbox_y, checkbox_size, is_gift_box_checked)
        
        text_x = gift_box_x + frame_width / 2
        text_y = frame_y + frame_height - 0.60 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, "GIFT BOX")
        
        text_y -= 0.25 * inch
        if row['Gift Box'] == "YES":
            c.setFont("Helvetica-BoldOblique", 14)
        else:
            c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, row['Gift Box'])
        
        gift_note_x = gift_box_x + frame_width + 0.2 * inch
        c.rect(gift_note_x, frame_y, frame_width, frame_height, stroke=1, fill=0)
        
        checkbox_x = gift_note_x + (frame_width - checkbox_size) / 2
        is_gift_note_checked = (row['Gift Note'] == "YES")
        draw_checkbox(c, checkbox_x, checkbox_y, checkbox_size, is_gift_note_checked)
        
        text_x = gift_note_x + frame_width / 2
        text_y = frame_y + frame_height - 0.60 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, "GIFT NOTE")
        
        text_y -= 0.25 * inch
        if row['Gift Note'] == "YES":
            c.setFont("Helvetica-BoldOblique", 14)
        else:
            c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(text_x, text_y, row['Gift Note'])

        c.showPage()

    c.save()
    buf.seek(0)
    return buf

def generate_gift_message_labels(dataframe):
    buf = BytesIO()
    page_size = landscape((4 * inch, 6 * inch))
    c = canvas.Canvas(buf, pagesize=page_size)
    W, H = page_size

    gift_orders = dataframe[dataframe['Gift Message'] != ""]

    if len(gift_orders) == 0:
        c.setFont("Helvetica", 14)
        c.drawCentredString(W / 2, H / 2, "No gift messages found in orders")
        c.showPage()
    else:
        for _, row in gift_orders.iterrows():
            c.setStrokeColor(colors.black)
            c.setLineWidth(3)
            c.rect(0.4 * inch, 0.4 * inch, W - 0.8 * inch, H - 0.8 * inch, stroke=1, fill=0)

            c.setFont("Times-BoldItalic", 18)
            message = row['Gift Message']
            
            words = message.split()
            lines = []
            current_line = []
            max_width = W - 1.2 * inch
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if c.stringWidth(test_line, "Times-BoldItalic", 18) < max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))

            total_height = len(lines) * 0.3 * inch
            y = (H + total_height) / 2

            for line in lines:
                c.drawCentredString(W / 2, y, line)
                y -= 0.3 * inch

            c.showPage()

    c.save()
    buf.seek(0)
    return buf

def generate_summary_pdf(dataframe, summary_stats):
    buf = BytesIO()
    from reportlab.lib.pagesizes import A4
    page_size = A4
    c = canvas.Canvas(buf, pagesize=page_size)
    W, H = page_size
    left = 0.75 * inch
    right = W - 0.75 * inch
    top = H - 0.75 * inch
    
    y = top
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, y, "END OF DAY SUMMARY")
    y -= 0.3 * inch
    
    from datetime import datetime
    today = datetime.now().strftime("%B %d, %Y")
    c.setFont("Helvetica", 14)
    c.drawCentredString(W / 2, y, f"Report Date: {today}")
    y -= 0.5 * inch
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    box_height = 2.5 * inch
    box_y = y - box_height
    c.rect(left, box_y, right - left, box_height, stroke=1, fill=0)
    
    y -= 0.3 * inch
    
    c.setFont("Helvetica-Bold", 16)
    col1_x = left + 0.5 * inch
    col2_x = W / 2 + 0.5 * inch
    
    c.drawString(col1_x, y, "Total Blankets:")
    c.drawRightString(col2_x - 0.3 * inch, y, str(summary_stats['total_blankets']))
    c.drawString(col2_x, y, "Total Beanies:")
    c.drawRightString(right - 0.5 * inch, y, str(summary_stats['total_beanies']))
    y -= 0.35 * inch
    
    c.drawString(col1_x, y, "Total Orders:")
    c.drawRightString(col2_x - 0.3 * inch, y, str(summary_stats['total_orders']))
    c.drawString(col2_x, y, "Gift Boxes:")
    c.drawRightString(right - 0.5 * inch, y, str(summary_stats['gift_boxes']))
    y -= 0.35 * inch
    
    c.drawString(col1_x, y, "Blanket Only:")
    c.drawRightString(col2_x - 0.3 * inch, y, str(summary_stats['blanket_only']))
    c.drawString(col2_x, y, "Gift Messages:")
    c.drawRightString(right - 0.5 * inch, y, str(summary_stats['gift_messages']))
    y -= 0.35 * inch
    
    c.drawString(col1_x, y, "With Beanie:")
    c.drawRightString(col2_x - 0.3 * inch, y, str(summary_stats['with_beanie']))
    c.drawString(col2_x, y, "Unique Colors:")
    c.drawRightString(right - 0.5 * inch, y, str(summary_stats['unique_colors']))
    
    y = box_y - 0.5 * inch
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Blanket Color Breakdown")
    y -= 0.3 * inch
    
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(left, y, right, y)
    y -= 0.25 * inch
    
    c.setFont("Helvetica", 14)
    for color, count in summary_stats['blanket_colors'].items():
        if y < 2 * inch:
            c.showPage()
            y = top
            c.setFont("Helvetica", 14)
        
        c.drawString(left + 0.3 * inch, y, f"{color}:")
        c.drawRightString(right - 0.3 * inch, y, str(count))
        y -= 0.22 * inch
    
    y -= 0.3 * inch
    
    if y < 3 * inch:
        c.showPage()
        y = top
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Thread Color Breakdown")
    y -= 0.3 * inch
    
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(left, y, right, y)
    y -= 0.25 * inch
    
    c.setFont("Helvetica", 14)
    for color, count in summary_stats['thread_colors'].items():
        if y < 1.5 * inch:
            c.showPage()
            y = top
            c.setFont("Helvetica", 14)
        
        c.drawString(left + 0.3 * inch, y, f"{color}:")
        c.drawRightString(right - 0.3 * inch, y, str(count))
        y -= 0.22 * inch
    
    y -= 0.5 * inch
    
    if y < 4 * inch:
        c.showPage()
        y = top
    
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, y, "Bobbin Color Setup")
    y -= 0.3 * inch
    
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(left, y, right, y)
    y -= 0.3 * inch
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left + 0.3 * inch, y, "⚫ Black Bobbin")
    c.drawRightString(right - 0.3 * inch, y, f"Total: {summary_stats['black_bobbin_total']}")
    y -= 0.25 * inch
    
    c.setFont("Helvetica", 13)
    for color, count in summary_stats['black_bobbin_threads'].items():
        if y < 1.5 * inch:
            c.showPage()
            y = top
            c.setFont("Helvetica", 13)
        c.drawString(left + 0.6 * inch, y, f"• {color}:")
        c.drawRightString(right - 0.3 * inch, y, str(count))
        y -= 0.2 * inch
    
    y -= 0.25 * inch
    
    if y < 2 * inch:
        c.showPage()
        y = top
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left + 0.3 * inch, y, "⚪ White Bobbin")
    c.drawRightString(right - 0.3 * inch, y, f"Total: {summary_stats['white_bobbin_total']}")
    y -= 0.25 * inch
    
    c.setFont("Helvetica", 13)
    for color, count in summary_stats['white_bobbin_threads'].items():
        if y < 1.5 * inch:
            c.showPage()
            y = top
            c.setFont("Helvetica", 13)
        c.drawString(left + 0.6 * inch, y, f"• {color}:")
        c.drawRightString(right - 0.3 * inch, y, str(count))
        y -= 0.2 * inch
    
    c.save()
    buf.seek(0)
    return buf

# --------------------------------------
# SIDEBAR WITH FUNCTIONAL NAVIGATION
# --------------------------------------
with st.sidebar:
    st.markdown("# 🧵 Blanket Manager")
    st.markdown("<div style='color:#9a978d; font-size:0.8em; letter-spacing:1px; text-transform:uppercase; margin-top:-10px;'>Order Processing Suite · v12.0</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("#### 🗂️ Sections")
    nav_section = st.radio(
        "Navigate",
        ["📊 Dashboard", "🎨 Colors", "🧵 Bobbins", "📥 Generate", "🔄 Merge"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("#### ✨ Features")
    st.markdown("✓ PDF Parsing")
    st.markdown("✓ Label Generation")
    st.markdown("✓ Sequence Merging")
    st.markdown("✓ Spanish Translation")

    st.markdown("---")
    st.markdown('<div class="status-indicator"><div class="status-dot"></div><span>System Ready</span></div>', unsafe_allow_html=True)

# --------------------------------------
# MAIN CONTENT
# --------------------------------------
st.title("🧵 Amazon Blanket Order Manager")

st.markdown("""
Professional order processing & label generation system  
Parse Amazon PDFs • Generate labels • Merge shipments
""")

st.markdown("---")

# File Upload Section
st.markdown("## 📄 Upload Order")
uploaded = st.file_uploader(
    "Drop your Amazon packing slip PDF here",
    type=["pdf"],
    help="Upload the packing slip PDF from your Amazon orders"
)

# --------------------------------------
# Parse PDF
# --------------------------------------
if uploaded:
    st.info("⏳ Reading and parsing your PDF...")

    all_pages = []
    with pdfplumber.open(uploaded) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_pages.append(text)

    records = []

    # Amazon packing slips put MULTIPLE orders on a single page, and an order can
    # span a page break. Parsing per-page captured only the first ship-to on each
    # page, leaving later orders with empty ZIPs. Instead, join all pages and
    # split into per-order segments anchored on "Ship To:" so each order carries
    # its own address, Order ID, and customization block.
    full_text = "\n".join(all_pages)

    # Each segment starts at a "Ship To:" and runs until the next "Ship To:".
    segments = re.split(r"(?=Ship To:)", full_text)

    for seg in segments:
        if "Order ID:" not in seg:
            continue  # not a real order segment

        # ----- ship-to / address (now scoped to THIS order) -----
        buyer_match = re.search(r"Ship To:\s*([\s\S]*?)Order ID:", seg)
        buyer_name = ""
        ship_to_full = ""
        ship_zip = ""
        ship_zip4 = ""
        ship_street_no = ""
        if buyer_match:
            lines = [l.strip() for l in buyer_match.group(1).splitlines() if l.strip()]
            if lines:
                buyer_name = lines[0]
            ship_to_full = " ".join(lines)
            ship_zip, ship_zip4 = extract_zip(ship_to_full)
            street_m = re.search(r"\b(\d{1,6})\b", normalize_zip_wrap(ship_to_full))
            if street_m:
                ship_street_no = street_m.group(1)

        order_id = ""
        order_date = ""
        m_id = re.search(r"Order ID:\s*([\d\-]+)", seg)
        if m_id:
            order_id = m_id.group(1).strip()
        m_date = re.search(r"Order Date:\s*([A-Za-z]{3,},?\s*[A-Za-z]+\s*\d{1,2},?\s*\d{4})", seg)
        if m_date:
            order_date = m_date.group(1).strip()

        page_text = seg  # keep downstream variable name working

        blocks = re.split(r"(?=Customizations:)", page_text)
        for block in blocks:
            if "Customizations:" not in block:
                continue

            qty_match = re.search(r"Quantity\s*\n\s*(\d+)", block)
            quantity = qty_match.group(1) if qty_match else "1"

            blanket_color = ""
            thread_color = ""
            b_match = re.search(r"Color:\s*([^\n]+)", block)
            if b_match:
                blanket_color = clean_text(b_match.group(1))
            t_match = re.search(r"Thread Color:\s*([^\n]+)", block, re.IGNORECASE)
            if t_match:
                thread_color = translate_thread_color(clean_text(t_match.group(1)))

            name_match = re.search(r"Name:\s*([^\n]+)", block)
            customization_name = clean_text(name_match.group(1)) if name_match else ""

            # Detect the Gift Box SKU (CL-IE0U-XBNJ) — sold as a "Blanket and Beanie
            # Set" gift box. Its block has no "Personalized Baby Beanie" or
            # "Gift Bag & Gift Card" line, so the normal regexes would read NO.
            # For this product the beanie is always included and it IS the gift box,
            # so we force both fields to YES.
            is_gift_box_sku = bool(
                re.search(r"SKU:\s*CL-IE0U-XBNJ", block, re.IGNORECASE)
                or re.search(r"Blanket and Beanie Set", block, re.IGNORECASE)
            )

            if is_gift_box_sku:
                beanie = "YES"
                gift_box = "YES"
            else:
                beanie = "YES" if re.search(r"Personalized Baby Beanie:\s*Yes", block, re.IGNORECASE) else "NO"
                gift_box = "YES" if re.search(r"Gift Bag\s*&\s*Gift Card:\s*Yes", block, re.IGNORECASE) else "NO"

            gift_note = "YES" if re.search(r"Gift Message:", block, re.IGNORECASE) else "NO"

            # Capture the gift message, including multi-line ones, stopping at the
            # first line that belongs to a different field. The previous pattern's
            # stop-list omitted the lines that actually follow a gift message
            # ("Add rush service?", "Please CHECK", etc.), so it captured nothing.
            gift_msg_match = re.search(
                r"Gift Message:\s*(.*?)"
                r"(?=\n\s*(?:Add rush service|Please CHECK|Personalized Baby|Gift Bag|"
                r"Gift Box|Blanket and Beanie|Surface\s*\d|Grand total|Item subtotal|"
                r"Item total|Shipping total|Tax|Promotion|Order Totals|"
                r"Returning your item|Visit|Quantity|SKU:)|\Z)",
                block,
                re.IGNORECASE | re.DOTALL
            )
            gift_message = ""
            if gift_msg_match:
                # collapse internal newlines (multi-line messages) into spaces
                raw_msg = re.sub(r"\s*\n\s*", " ", gift_msg_match.group(1))
                gift_message = clean_text(raw_msg)

            records.append({
                "Order ID": order_id,
                "Order Date": order_date,
                "Buyer Name": buyer_name,
                "Ship To Full": ship_to_full,
                "Ship ZIP": ship_zip,
                "Ship ZIP4": ship_zip4,
                "Ship Street No": ship_street_no,
                "Quantity": quantity,
                "Blanket Color": blanket_color,
                "Thread Color": thread_color,
                "Customization Name": customization_name,
                "Include Beanie": beanie,
                "Gift Box": gift_box,
                "Gift Note": gift_note,
                "Gift Message": gift_message
            })

        # Fallback: some listings (e.g. the "Blue Blanket" SKU) have NO
        # "Customizations:" block, so the loop above produces no record and the
        # order would silently vanish — no manufacturing label, no shipping-label
        # match, wrong counts. If this page had an Order ID but yielded nothing,
        # add a minimal record so the order is still processed and matched.
        if order_id and not any(r["Order ID"] == order_id for r in records):
            sku_m = re.search(r"SKU:\s*([^\n]+)", page_text)
            prod_sku = clean_text(sku_m.group(1)) if sku_m else ""
            records.append({
                "Order ID": order_id,
                "Order Date": order_date,
                "Buyer Name": buyer_name,
                "Ship To Full": ship_to_full,
                "Ship ZIP": ship_zip,
                "Ship ZIP4": ship_zip4,
                "Ship Street No": ship_street_no,
                "Quantity": "1",
                "Blanket Color": "",
                "Thread Color": "",
                "Customization Name": f"⚠ NO CUSTOMIZATION DATA (SKU: {prod_sku})",
                "Include Beanie": "NO",
                "Gift Box": "NO",
                "Gift Note": "NO",
                "Gift Message": ""
            })

    if not records:
        st.error("❌ No orders detected. Please check your PDF format.")
        st.stop()

    df = pd.DataFrame(records)
    df.index = df.index + 1
    
    st.success(f"✅ Successfully parsed {len(df)} line items from {df['Order ID'].nunique()} orders")
    
    with st.expander("📊 View Order Data"):
        st.dataframe(df, use_container_width=True)

    # --------------------------------------
    # Calculate Summary Statistics
    # --------------------------------------
    df['Quantity_Int'] = df['Quantity'].astype(int)
    
    total_blankets = df['Quantity_Int'].sum()
    total_beanies = df[df['Include Beanie'] == 'YES']['Quantity_Int'].sum()
    total_orders = df['Order ID'].nunique()
    orders_blanket_only = len(df[df['Include Beanie'] == 'NO'])
    orders_with_beanie = len(df[df['Include Beanie'] == 'YES'])
    gift_boxes_needed = len(df[df['Gift Box'] == 'YES'])
    gift_messages_needed = len(df[df['Gift Note'] == 'YES'])
    
    blanket_color_counts = df.groupby('Blanket Color')['Quantity_Int'].sum().sort_values(ascending=False)
    thread_color_counts = df.groupby('Thread Color')['Quantity_Int'].sum().sort_values(ascending=False)
    
    df['Bobbin_Color'] = df['Thread Color'].apply(get_bobbin_color)
    bobbin_counts = df.groupby('Bobbin_Color')['Quantity_Int'].sum()
    
    black_bobbin_df = df[df['Bobbin_Color'] == 'Black Bobbin']
    white_bobbin_df = df[df['Bobbin_Color'] == 'White Bobbin']
    
    black_bobbin_threads = black_bobbin_df.groupby('Thread Color')['Quantity_Int'].sum().sort_values(ascending=False)
    white_bobbin_threads = white_bobbin_df.groupby('Thread Color')['Quantity_Int'].sum().sort_values(ascending=False)

    # --------------------------------------
    # Guided progress strip (light) — sections driven by sidebar nav
    # --------------------------------------
    st.markdown("---")

    _has_mfg = st.session_state.get("manufacturing_labels_buffer") is not None
    _steps = [
        ("Upload", True),
        ("Review", True),
        ("Generate", _has_mfg),
        ("Merge", False),
    ]
    _chips = []
    for _i, (_label, _done) in enumerate(_steps, start=1):
        if _done:
            _bg, _fg, _mark = "#b5623c", "#ffffff", "✓"
        else:
            _bg, _fg, _mark = "#efece5", "#9a978d", str(_i)
        _txt = "#26251f" if _done else "#9a978d"
        _chips.append(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="width:24px;height:24px;border-radius:50%;background:{_bg};color:{_fg};'
            f'display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;">{_mark}</div>'
            f'<span style="font-size:13px;color:{_txt};font-weight:600;">{_label}</span></div>'
        )
    _connector = '<div style="flex:1;height:2px;background:#e9e6df;margin:0 8px;"></div>'
    _strip = '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 2px 18px;">' + _connector.join(_chips) + '</div>'
    st.markdown(_strip, unsafe_allow_html=True)

    if nav_section == "📊 Dashboard":
        st.markdown("## 📊 Order Dashboard")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Total Blankets", total_blankets)
        with col2:
            st.metric("Total Orders", total_orders)
        with col3:
            st.metric("Beanies", total_beanies)
        with col4:
            st.metric("Gift Boxes", gift_boxes_needed)
        with col5:
            st.metric("Gift Messages", gift_messages_needed)
        with col6:
            st.metric("Unique Colors", len(blanket_color_counts))

        col7, col8 = st.columns(2)
        with col7:
            st.metric("Blanket Only", orders_blanket_only)
        with col8:
            st.metric("With Beanie", orders_with_beanie)

    if nav_section == "🎨 Colors":
        st.markdown("## 🎨 Color Analytics")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 🧶 Blanket Colors")
            for color, count in blanket_color_counts.items():
                st.markdown(f"**{color}:** {count}")

        with col_right:
            st.markdown("### 🧵 Thread Colors")
            for color, count in thread_color_counts.items():
                st.markdown(f"**{color}:** {count}")

    if nav_section == "🧵 Bobbins":
        st.markdown("## 🧵 Bobbin Color Configuration")

        col_bobbin1, col_bobbin2 = st.columns(2)

        with col_bobbin1:
            st.markdown("### ⚫ Black Bobbin")
            st.metric("Total Items", bobbin_counts.get('Black Bobbin', 0))
            if len(black_bobbin_threads) > 0:
                for color, count in black_bobbin_threads.items():
                    st.markdown(f"• **{color}:** {count}")
            else:
                st.markdown("_No items_")

        with col_bobbin2:
            st.markdown("### ⚪ White Bobbin")
            st.metric("Total Items", bobbin_counts.get('White Bobbin', 0))
            if len(white_bobbin_threads) > 0:
                for color, count in white_bobbin_threads.items():
                    st.markdown(f"• **{color}:** {count}")
            else:
                st.markdown("_No items_")

    if nav_section == "📥 Generate":
        st.markdown("## 📥 Generate & Download")

        if 'manufacturing_labels_buffer' not in st.session_state:
            st.session_state.manufacturing_labels_buffer = None

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📦 Manufacturing Labels", use_container_width=True):
                with st.spinner("Generating manufacturing labels..."):
                    pdf_data = generate_manufacturing_labels(df)
                    st.session_state.manufacturing_labels_buffer = pdf_data
                st.success("✅ Labels generated!")
                st.download_button(
                    label="⬇️ Download Manufacturing Labels",
                    data=pdf_data,
                    file_name="Manufacturing_Labels.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with col2:
            gift_count = len(df[df['Gift Message'] != ""])
            if st.button(f"💌 Gift Messages ({gift_count})", use_container_width=True):
                with st.spinner("Generating gift message labels..."):
                    pdf_data = generate_gift_message_labels(df)
                st.success("✅ Labels generated!")
                st.download_button(
                    label="⬇️ Download Gift Message Labels",
                    data=pdf_data,
                    file_name="Gift_Message_Labels.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with col3:
            if st.button("📊 Summary Report", use_container_width=True):
                with st.spinner("Generating summary report..."):
                    summary_stats = {
                        'total_blankets': total_blankets,
                        'total_beanies': total_beanies,
                        'total_orders': total_orders,
                        'blanket_only': orders_blanket_only,
                        'with_beanie': orders_with_beanie,
                        'gift_boxes': gift_boxes_needed,
                        'gift_messages': gift_messages_needed,
                        'unique_colors': len(blanket_color_counts),
                        'blanket_colors': blanket_color_counts.to_dict(),
                        'thread_colors': thread_color_counts.to_dict(),
                        'black_bobbin_total': int(bobbin_counts.get('Black Bobbin', 0)),
                        'white_bobbin_total': int(bobbin_counts.get('White Bobbin', 0)),
                        'black_bobbin_threads': black_bobbin_threads.to_dict() if len(black_bobbin_threads) > 0 else {},
                        'white_bobbin_threads': white_bobbin_threads.to_dict() if len(white_bobbin_threads) > 0 else {}
                    }
                    pdf_data = generate_summary_pdf(df, summary_stats)
                st.success("✅ Report generated!")
                st.download_button(
                    label="⬇️ Download Summary PDF",
                    data=pdf_data,
                    file_name="Daily_Summary_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    if nav_section == "🔄 Merge":
        st.markdown("## 🔄 Merge Shipping & Manufacturing Labels")

        st.info("""
        **How merging works:**
        Labels are paired to orders **by sequence** — the 1st shipping label goes with
        the 1st order, the 2nd with the 2nd, and so on, following your order-detail order.
        The merged PDF gives each order its shipping label + manufacturing label(s).
        If there are fewer labels than orders, the leftover orders get a **warning label**
        so nothing ships blank. A trailing "successful label purchase" summary page is
        skipped automatically.

        ⚠️ **Important:** make sure your shipping labels are in the **same order** as your
        order-details PDF before merging.

        1. Generate Manufacturing Labels above
        2. Upload your shipping labels PDF (in order)
        3. Click merge
        """)

        if not OCR_AVAILABLE:
            st.caption(
                "Note: OCR isn't active here. Sequence merging works without it — OCR "
                "only matters for the diagnostic text-read of photo labels."
            )
        _skip_ocr_warn = True

        if not _skip_ocr_warn and not OCR_AVAILABLE:
            st.warning(
                "⚠️ OCR is not available in this environment, so **photo/scanned** labels "
                "can't be read (clean digital labels still work). To enable OCR on Streamlit "
                "Cloud, add `tesseract-ocr` and `poppler-utils` to `packages.txt` and "
                "`pytesseract`, `pdf2image`, `Pillow` to `requirements.txt`."
            )

        shipping_labels_upload = st.file_uploader(
            "📤 Upload Shipping Labels PDF",
            type=["pdf"],
            key="shipping_labels",
            help="Upload the shipping labels PDF from Amazon or your carrier"
        )

        # ---- Diagnostic: see exactly what the app reads from each label ----
        if shipping_labels_upload:
            with st.expander("🔬 Diagnostic — what the app reads from each shipping label"):
                st.caption(
                    "Use this to see why labels match or don't. For each page it shows the "
                    "extracted ZIP / street number and a snippet of the raw text. If the ZIP "
                    "column is blank on clean labels, that's an extraction issue; if the text "
                    "snippet is empty on a photo label, OCR isn't reading it."
                )
                if st.button("🔍 Scan shipping labels (diagnostic)", use_container_width=True):
                    shipping_labels_upload.seek(0)
                    try:
                        diag_pdf = PdfReader(shipping_labels_upload)
                    except Exception as e:
                        st.error(f"Couldn't open the shipping PDF: {e}")
                        diag_pdf = None

                    if diag_pdf:
                        st.write(f"**OCR available:** {'✅ yes' if OCR_AVAILABLE else '❌ no (photo labels can’t be read)'}")
                        st.write(f"**Pages in shipping PDF:** {len(diag_pdf.pages)}")

                        # what the orders expect, for quick cross-reference
                        order_zips = sorted({
                            f"{r['Ship ZIP']}-{r['Ship ZIP4']}".rstrip('-')
                            for _, r in df.iterrows() if r.get('Ship ZIP')
                        })
                        st.write("**ZIP codes expected from your orders:**")
                        st.code(", ".join(order_zips) if order_zips else "(none extracted from orders!)")

                        rows = []
                        for pidx, page in enumerate(diag_pdf.pages):
                            shipping_labels_upload.seek(0)
                            txt = _read_label_page_text(page, pidx, shipping_labels_upload)
                            low = (txt or "").lower()
                            is_manifest = ("successful label purchase" in low or "list of orders" in low)
                            if is_manifest:
                                rows.append({
                                    "Page": pidx + 1, "Type": "MANIFEST (skipped)",
                                    "ZIP": "", "Street#": "",
                                    "Text length": len(txt or ""),
                                    "Raw snippet": (txt or "")[:80].replace("\n", " ")
                                })
                                continue
                            keys = extract_label_keys(txt)
                            rows.append({
                                "Page": pidx + 1,
                                "Type": "label",
                                "ZIP": f"{keys['zip5']}-{keys['zip4']}".rstrip("-"),
                                "Street#": keys["street_no"],
                                "Text length": len(txt or ""),
                                "Raw snippet": (txt or "")[:80].replace("\n", " "),
                            })
                        diag_df = pd.DataFrame(rows)
                        st.dataframe(diag_df, use_container_width=True)

                        blank_zip = diag_df[(diag_df["Type"] == "label") & (diag_df["ZIP"] == "")]
                        if len(blank_zip) > 0:
                            st.warning(
                                f"⚠️ {len(blank_zip)} label page(s) produced NO ZIP. "
                                "If their 'Text length' is near 0 → OCR isn't reading a photo label. "
                                "If text is present but ZIP is blank → send me that raw snippet and "
                                "I'll fix the extraction for that label format."
                            )

        if shipping_labels_upload and st.session_state.manufacturing_labels_buffer:
            col_merge1, col_merge2 = st.columns([3, 1])

            with col_merge1:
                if st.button("🔀 Merge Labels Now", type="primary", use_container_width=True):
                    with st.spinner("Merging labels by sequence..."):
                        shipping_labels_upload.seek(0)
                        st.session_state.manufacturing_labels_buffer.seek(0)

                        merged_pdf, n_matched, n_unmatched, unmatched_orders, leftover_labels = \
                            merge_shipping_and_manufacturing_labels(
                                shipping_labels_upload,
                                st.session_state.manufacturing_labels_buffer,
                                df
                            )

                        if merged_pdf:
                            st.success(
                                f"✅ Paired {n_matched} order(s) with a shipping label. "
                                f"{n_unmatched} order(s) had no label (warning label inserted)."
                            )

                            if n_unmatched > 0:
                                with st.expander(f"⚠️ {n_unmatched} order(s) with NO label — review", expanded=True):
                                    for o in unmatched_orders:
                                        st.write(f"• **{o['Buyer Name']}** ({o['Order ID']}) — {o.get('Ship To Full','')}")

                            if leftover_labels:
                                with st.expander(f"📦 {len(leftover_labels)} extra shipping label(s) — more labels than orders"):
                                    st.write(
                                        "There were more shipping labels than orders. "
                                        "The extras are appended at the end of the merged PDF for manual review."
                                    )

                            multi_item_orders = df.groupby('Order ID').size()
                            multi_item_orders = multi_item_orders[multi_item_orders > 1]
                            if len(multi_item_orders) > 0:
                                with st.expander(f"ℹ️ {len(multi_item_orders)} order(s) with multiple items"):
                                    for order_id, count in multi_item_orders.items():
                                        buyer = df[df['Order ID'] == order_id]['Buyer Name'].iloc[0]
                                        st.write(f"• {buyer} ({order_id}): {count} blankets")

                            st.download_button(
                                label="⬇️ Download Merged Labels PDF",
                                data=merged_pdf,
                                file_name="Merged_Shipping_Manufacturing_Labels.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )

            with col_merge2:
                st.metric("Total Orders", df['Order ID'].nunique())
                st.metric("Total Items", len(df))

        elif shipping_labels_upload and not st.session_state.manufacturing_labels_buffer:
            st.warning("⚠️ Please generate Manufacturing Labels first (click the button above)")

        elif not shipping_labels_upload and st.session_state.manufacturing_labels_buffer:
            st.info("📤 Upload your shipping labels PDF above to enable merging")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #9a978d; padding: 20px;'>
    <p><strong style="color:#6b6960;">Amazon Blanket Order Manager · v12.0</strong></p>
    <p>Professional order processing &amp; label generation system</p>
</div>
""", unsafe_allow_html=True)

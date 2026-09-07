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
    /* Dark Mode Base */
    .main {
        background: #0f1419;
        color: #e4e6eb;
    }
    
    .stApp {
        background: #0f1419;
    }
    
    /* Sidebar Dark Styling */
    [data-testid="stSidebar"] {
        background: #1a1f2e;
        border-right: 1px solid #2d3748;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #e4e6eb;
    }
    
    /* Sidebar Navigation Links */
    .nav-link {
        display: block;
        padding: 12px 15px;
        margin: 4px 0;
        border-radius: 10px;
        color: #a0aec0;
        text-decoration: none;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .nav-link:hover {
        background: #2d3748;
        color: #e4e6eb;
        text-decoration: none;
    }
    
    .nav-link.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Metric Cards Dark */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e2432 0%, #252d3d 100%);
        border: 1px solid #2d3748;
        padding: 25px 20px;
        border-radius: 16px;
        border-left: 3px solid #667eea;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
        border-color: #667eea;
    }
    
    [data-testid="stMetric"] label {
        font-size: 0.85em !important;
        color: #a0aec0 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 2.5em !important;
        font-weight: 700 !important;
        color: #e4e6eb !important;
    }
    
    /* Headers Dark */
    h1 {
        color: #e4e6eb;
        font-weight: 700;
        padding-bottom: 15px;
        border-bottom: 3px solid #667eea;
        margin-bottom: 30px;
    }
    
    h2 {
        color: #e4e6eb;
        font-weight: 600;
        margin-top: 40px;
        margin-bottom: 20px;
    }
    
    h3 {
        color: #cbd5e0;
        font-weight: 600;
        margin-bottom: 15px;
    }
    
    /* Buttons Dark */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* File Uploader Dark */
    [data-testid="stFileUploader"] {
        background: #1a1f2e;
        padding: 40px;
        border-radius: 12px;
        border: 2px dashed #2d3748;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #667eea;
        background: #1e2432;
    }
    
    [data-testid="stFileUploader"] label {
        color: #e4e6eb !important;
    }
    
    [data-testid="stFileUploader"] section {
        border-color: #2d3748 !important;
    }
    
    /* Info boxes Dark */
    .stAlert {
        background: linear-gradient(135deg, #667eea20, #764ba220) !important;
        border: 1px solid #667eea40 !important;
        border-radius: 10px;
        border-left: 4px solid #667eea !important;
        color: #cbd5e0 !important;
    }
    
    /* Success boxes */
    [data-baseweb="notification"] {
        background: #1a1f2e !important;
        border: 1px solid #48bb78 !important;
        color: #e4e6eb !important;
    }
    
    /* Dataframe Dark */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }
    
    [data-testid="stDataFrame"] table {
        background: #1a1f2e !important;
        color: #e4e6eb !important;
    }
    
    [data-testid="stDataFrame"] thead tr th {
        background: #2d3748 !important;
        color: #e4e6eb !important;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        background: #1e2432 !important;
        color: #cbd5e0 !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background: #252d3d !important;
    }
    
    /* Expander Dark */
    [data-testid="stExpander"] {
        background: #1a1f2e !important;
        border-radius: 10px;
        border: 1px solid #2d3748 !important;
        margin-bottom: 10px;
    }
    
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
        color: #e4e6eb !important;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Download button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 5px 15px rgba(72, 187, 120, 0.4);
    }
    
    /* Text color overrides */
    p, span, div {
        color: #cbd5e0;
    }
    
    strong {
        color: #e4e6eb;
    }
    
    /* Section divider */
    hr {
        border: none;
        border-top: 1px solid #2d3748;
        margin: 40px 0;
    }
    
    /* Spinner Dark */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Input fields */
    input, textarea, select {
        background: #1a1f2e !important;
        color: #e4e6eb !important;
        border: 1px solid #2d3748 !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #cbd5e0 !important;
    }
    
    /* Status indicator */
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #2d3748;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85em;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        background: #48bb78;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
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
    # Prefer text after a ship-to / deliver-to marker
    marker = re.search(r"(ship\s*to|deliver\s*to)\s*:?", text, re.IGNORECASE)
    if marker:
        work = text[marker.end():]
    else:
        # No marker (e.g. rough OCR) — strip the known sender block if present
        work = re.sub(r"[\s\S]*?FAIRFIELD[^\n]*07004[^\n]*", "", text, count=1, flags=re.IGNORECASE) or text

    zip_m = re.search(r"(\d{5})(?:-(\d{4}))?", work)
    if zip_m:
        keys["zip5"] = zip_m.group(1)
        keys["zip4"] = zip_m.group(2) or ""

    street_m = re.search(r"\b(\d{1,6})\b", work)
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
    try:
        shipping_pdf = PdfReader(shipping_pdf_bytes)
        manufacturing_pdf = PdfReader(manufacturing_pdf_bytes)

        # ---- build ordered list of unique orders (master spine) ----
        orders = []
        seen = set()
        # mfg labels are generated per-row in dataframe order; track row ranges
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
                    "Ship ZIP": r.get("Ship ZIP", ""),
                    "Ship ZIP4": r.get("Ship ZIP4", ""),
                    "Ship Street No": r.get("Ship Street No", ""),
                })

        # ---- read every shipping-label page and extract keys ----
        label_keys_list = []
        for pidx, page in enumerate(shipping_pdf.pages):
            txt = _read_label_page_text(page, pidx, shipping_pdf_bytes)
            label_keys_list.append(extract_label_keys(txt))

        # ---- match each label to an order ----
        order_to_label = {}   # order_id -> shipping page index
        used_order_ids = set()
        for pidx, keys in enumerate(label_keys_list):
            idx, conf = match_label_to_order(keys, orders, used_order_ids)
            if idx is not None:
                oid = orders[idx]["Order ID"]
                order_to_label[oid] = pidx
                used_order_ids.add(oid)

        leftover_labels = [
            pidx for pidx in range(len(label_keys_list))
            if pidx not in set(order_to_label.values())
        ]

        # ---- assemble output in master (order-detail) sequence ----
        output_pdf = PdfWriter()
        n_matched = 0
        unmatched_orders = []

        for o in orders:
            oid = o["Order ID"]
            mfg_pages = row_positions.get(oid, [])

            if oid in order_to_label:
                output_pdf.add_page(shipping_pdf.pages[order_to_label[oid]])
                n_matched += 1
            else:
                warn = make_warning_label(o)
                warn_reader = PdfReader(warn)
                output_pdf.add_page(warn_reader.pages[0])
                unmatched_orders.append(o)

            for mi in mfg_pages:
                if mi < len(manufacturing_pdf.pages):
                    output_pdf.add_page(manufacturing_pdf.pages[mi])

        # ---- append leftover (unused) shipping labels at the very end ----
        if leftover_labels:
            note = BytesIO()
            page_size = landscape((4 * inch, 6 * inch))
            cc = canvas.Canvas(note, pagesize=page_size)
            Wc, Hc = page_size
            cc.setFont("Helvetica-Bold", 18)
            cc.drawCentredString(Wc / 2, Hc / 2 + 0.3 * inch, "UNUSED SHIPPING LABELS")
            cc.setFont("Helvetica", 12)
            cc.drawCentredString(Wc / 2, Hc / 2 - 0.1 * inch,
                                 f"{len(leftover_labels)} label(s) matched no order — review below")
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
    st.markdown("### Version 11.0 Dark")
    st.markdown("---")
    
    st.markdown("#### 📋 Quick Navigation")
    
    # Functional navigation links with anchor tags
    st.markdown('<a href="#upload-order" class="nav-link">📄 Upload Order</a>', unsafe_allow_html=True)
    st.markdown('<a href="#dashboard" class="nav-link">📊 Dashboard</a>', unsafe_allow_html=True)
    st.markdown('<a href="#color-analytics" class="nav-link">🎨 Color Analytics</a>', unsafe_allow_html=True)
    st.markdown('<a href="#bobbin-setup" class="nav-link">🧵 Bobbin Setup</a>', unsafe_allow_html=True)
    st.markdown('<a href="#generate-labels" class="nav-link">📥 Generate Labels</a>', unsafe_allow_html=True)
    st.markdown('<a href="#label-merge" class="nav-link">🔄 Label Merge</a>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("#### ✨ Features")
    st.markdown("✓ PDF Parsing")
    st.markdown("✓ Label Generation")
    st.markdown("✓ Order Merging")
    st.markdown("✓ Spanish Translation")
    
    st.markdown("---")
    st.markdown('<div class="status-indicator"><div class="status-dot"></div><span>System Ready</span></div>', unsafe_allow_html=True)

# --------------------------------------
# MAIN CONTENT
# --------------------------------------
st.title("🧵 Amazon Blanket Order Manager")

st.markdown("""
**Professional order processing & label generation system**  
Parse Amazon PDFs • Generate labels • Merge shipments
""")

st.markdown("---")

# File Upload Section with anchor
st.markdown('<a id="upload-order"></a>', unsafe_allow_html=True)
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

    for page_text in all_pages:
        buyer_match = re.search(r"Ship To:\s*([\s\S]*?)Order ID:", page_text)
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
            # ZIP+4 (preferred) or plain 5-digit ZIP, from the full ship-to block
            zip_m = re.search(r"(\d{5})(?:-(\d{4}))?", ship_to_full)
            if zip_m:
                ship_zip = zip_m.group(1)
                ship_zip4 = zip_m.group(2) or ""
            # leading street number = first standalone run of digits in the block
            street_m = re.search(r"\b(\d{1,6})\b", ship_to_full)
            if street_m:
                ship_street_no = street_m.group(1)

        order_id = ""
        order_date = ""
        m_id = re.search(r"Order ID:\s*([\d\-]+)", page_text)
        if m_id:
            order_id = m_id.group(1).strip()
        m_date = re.search(r"Order Date:\s*([A-Za-z]{3,},?\s*[A-Za-z]+\s*\d{1,2},?\s*\d{4})", page_text)
        if m_date:
            order_date = m_date.group(1).strip()


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
    # Dashboard Metrics with anchor
    # --------------------------------------
    st.markdown("---")
    st.markdown('<a id="dashboard"></a>', unsafe_allow_html=True)
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
    
    # --------------------------------------
    # Color Breakdown with anchor
    # --------------------------------------
    st.markdown("---")
    st.markdown('<a id="color-analytics"></a>', unsafe_allow_html=True)
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
    
    # --------------------------------------
    # Bobbin Setup Section with anchor
    # --------------------------------------
    st.markdown("---")
    st.markdown('<a id="bobbin-setup"></a>', unsafe_allow_html=True)
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

    # --------------------------------------
    # Generate Labels Section with anchor
    # --------------------------------------
    st.markdown("---")
    st.markdown('<a id="generate-labels"></a>', unsafe_allow_html=True)
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
    
    # --------------------------------------
    # Label Merging Section with anchor
    # --------------------------------------
    st.markdown("---")
    st.markdown('<a id="label-merge"></a>', unsafe_allow_html=True)
    st.markdown("## 🔄 Merge Shipping & Manufacturing Labels")
    
    st.info("""
    **How matching works now:**
    Labels are matched to orders by **shipping address** (ZIP+4 → ZIP + street number → name),
    not by page order. The merged PDF follows your **order-detail sequence**. Any order whose
    label can't be matched gets a **warning label** in its place (manufacturing label still included),
    and unused labels are listed at the end.

    1. Generate Manufacturing Labels above
    2. Upload your shipping labels PDF
    3. Click merge
    """)

    if not OCR_AVAILABLE:
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
    
    if shipping_labels_upload and st.session_state.manufacturing_labels_buffer:
        col_merge1, col_merge2 = st.columns([3, 1])
        
        with col_merge1:
            if st.button("🔀 Merge Labels Now", type="primary", use_container_width=True):
                with st.spinner("Reading labels and matching by address..."):
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
                            f"✅ Matched {n_matched} order(s) to a shipping label. "
                            f"{n_unmatched} order(s) had no match (warning label inserted)."
                        )

                        if n_unmatched > 0:
                            with st.expander(f"⚠️ {n_unmatched} order(s) with NO matched label — review", expanded=True):
                                for o in unmatched_orders:
                                    st.write(f"• **{o['Buyer Name']}** ({o['Order ID']}) — {o['Ship To Full']}")

                        if leftover_labels:
                            with st.expander(f"📦 {len(leftover_labels)} unused shipping label(s) — matched no order"):
                                st.write(
                                    "These label pages didn't match any order in this batch. "
                                    "They're appended at the end of the merged PDF for manual review."
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
<div style='text-align: center; color: #a0aec0; padding: 20px;'>
    <p><strong>Amazon Blanket Order Manager v11.0 Dark</strong></p>
    <p>Professional order processing & label generation system</p>
</div>
""", unsafe_allow_html=True)

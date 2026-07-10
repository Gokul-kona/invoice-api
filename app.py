from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Invoice(BaseModel):
    invoice_text: str


def parse_money(value):
    if value is None:
        return None
    value = value.replace(",", "").strip()
    try:
        return float(value)
    except:
        return None


def search_patterns(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


@app.post("/extract")
def extract(data: Invoice):

    text = data.invoice_text

    # ---------------- Invoice Number ----------------

    invoice_no = search_patterns([
        r"Invoice\s*(?:No|Number|#)\s*[:#]?\s*([^\n\r]+)",
        r"Ref(?:erence)?\s*[:#]?\s*([^\n\r]+)",
        r"Bill\s*No\s*[:#]?\s*([^\n\r]+)",
    ], text)

    # ---------------- Date ----------------

    raw_date = search_patterns([
        r"Invoice\s*Date\s*[:#]?\s*([^\n\r]+)",
        r"Date\s*[:#]?\s*([^\n\r]+)",
        r"Issued\s*[:#]?\s*([^\n\r]+)",
        r"Issue\s*Date\s*[:#]?\s*([^\n\r]+)",
    ], text)

    date = None
    if raw_date:
        try:
            date = parser.parse(raw_date, dayfirst=True).date().isoformat()
        except:
            pass

    # ---------------- Vendor ----------------

    vendor = search_patterns([
        r"Vendor\s*[:#]?\s*([^\n\r]+)",
        r"Supplier\s*[:#]?\s*([^\n\r]+)",
        r"Seller\s*[:#]?\s*([^\n\r]+)",
        r"Merchant\s*[:#]?\s*([^\n\r]+)",
        r"Company\s*[:#]?\s*([^\n\r]+)",
        r"Sold\s*By\s*[:#]?\s*([^\n\r]+)",
        r"From\s*[:#]?\s*([^\n\r]+)",
    ], text)

    # ---------------- Currency ----------------

    cur = search_patterns([
        r"Currency\s*[:#]?\s*([A-Za-z]{3})"
    ], text)

    if cur:
        currency = cur.upper()
    elif "₹" in text or "Rs." in text or "Rs " in text:
        currency = "INR"
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    else:
        currency = None

    # ---------------- Amount ----------------

    amount = None

    amount_patterns = [
        r"Subtotal.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Taxable\s*Value.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Base\s*Amount.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Net\s*Amount.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*[:#]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for p in amount_patterns:
        m = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if m:
            amount = parse_money(m.group(1))
            break

    # ---------------- Tax ----------------

    tax = None

    tax_patterns = [
        r"IGST.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"CGST.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"SGST.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"GST.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"VAT.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for p in tax_patterns:
        m = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if m:
            tax = parse_money(m.group(1))
            break

    # ---------------- Fallback ----------------

    if amount is None or tax is None:
        nums = [
            parse_money(x)
            for x in re.findall(
                r"(?:Rs\.?|₹|\$)\s*([\d,]+(?:\.\d+)?)",
                text
            )
        ]

        nums = [n for n in nums if n is not None]

        if len(nums) >= 2:
            if amount is None:
                amount = nums[0]
            if tax is None:
                tax = nums[1]

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency,
    }
"""Simulated airline checkout used by mock search results.

It lets the Flutter WebView PNR-detection flow be exercised end-to-end
without a real booking. Real providers deep-link to the airline instead.
"""

from html import escape

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.services.flight_search import airline_name

router = APIRouter(prefix="/demo", tags=["demo"], include_in_schema=False)

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{airline} - Business Class Checkout</title>
<style>
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,sans-serif; background:#f4f1ea; color:#1d1d1f; }}
  header {{ background:#0b1f3a; color:#fff; padding:18px 20px; font-weight:600; letter-spacing:.5px; }}
  main {{ max-width:560px; margin:0 auto; padding:20px; }}
  .card {{ background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 10px rgba(0,0,0,.06); margin-bottom:16px; }}
  .row {{ display:flex; justify-content:space-between; margin:6px 0; }}
  label {{ display:block; font-size:13px; color:#555; margin-top:12px; }}
  input {{ width:100%; box-sizing:border-box; padding:12px; border:1px solid #ccc; border-radius:8px; font-size:16px; }}
  button {{ width:100%; margin-top:18px; padding:14px; border:0; border-radius:8px; background:#b8860b; color:#fff; font-size:16px; font-weight:600; }}
  .muted {{ color:#666; font-size:13px; }}
  #confirmation {{ display:none; }}
  .code {{ font-size:28px; font-weight:700; letter-spacing:4px; color:#0b1f3a; }}
</style>
</head>
<body>
<header>{airline} &middot; Business Class</header>
<main>
  <div class="card">
    <div class="row"><strong>{flight}</strong><span>{date}</span></div>
    <div class="row"><span>{origin} &rarr; {destination}</span><span>Business (J/C)</span></div>
    <div class="row"><span>Total fare</span><strong>{currency} {price}</strong></div>
  </div>

  <form id="checkout" class="card" onsubmit="return confirmBooking(event)">
    <strong>Passenger details</strong>
    <label>First name</label><input name="first" required autocomplete="given-name">
    <label>Last name</label><input name="last" required autocomplete="family-name">
    <label>Email</label><input name="email" type="email" required autocomplete="email">
    <button type="submit">Confirm &amp; Pay</button>
    <p class="muted">Demo checkout. No payment is taken.
      <a href="{airline_url}">Continue on the {airline} website instead</a>.</p>
  </form>

  <div id="confirmation" class="card">
    <h2>Booking confirmed</h2>
    <p>Thank you, <span id="pax"></span>. Your trip is booked.</p>
    <p>Confirmation: <span class="code" id="pnr"></span></p>
    <p class="muted">Keep this record locator for check-in and trip management.</p>
  </div>
</main>
<script>
  function confirmBooking(e) {{
    e.preventDefault();
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 6; i++) code += alphabet[Math.floor(Math.random() * alphabet.length)];
    const f = e.target;
    document.getElementById('pax').textContent = f.first.value + ' ' + f.last.value;
    document.getElementById('pnr').textContent = code;
    f.style.display = 'none';
    setTimeout(() => {{ document.getElementById('confirmation').style.display = 'block'; }}, 900);
    return false;
  }}
</script>
</body>
</html>"""


@router.get("/checkout", response_class=HTMLResponse)
async def demo_checkout(
    carrier: str = Query("DL", max_length=2),
    flight: str = Query("DL1", max_length=10),
    origin: str = Query("JFK", max_length=3),
    destination: str = Query("LHR", max_length=3),
    date: str = Query("", max_length=10),
    price: str = Query("0", max_length=10),
    currency: str = Query("USD", max_length=3),
    airline_url: str = Query("https://www.google.com/travel/flights", max_length=1024),
) -> HTMLResponse:
    safe_url = airline_url if airline_url.startswith(("https://", "http://")) else "#"
    html = _PAGE.format(
        airline=escape(airline_name(carrier)),
        flight=escape(flight),
        origin=escape(origin),
        destination=escape(destination),
        date=escape(date),
        price=escape(price),
        currency=escape(currency),
        airline_url=escape(safe_url, quote=True),
    )
    return HTMLResponse(html)

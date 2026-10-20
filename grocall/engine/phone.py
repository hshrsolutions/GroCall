"""The one place phone numbers are normalised (grocall-prd.md §4).

normalize("098765 43210") -> "+919876543210" (default country +91). Service/short codes
(fewer than 7 digits) are not E.164-able and come back as None; callers keep the raw text."""

import re

from grocall.engine.common import settings


def default_cc():
	try:
		cc = settings().default_country_code or "+91"
	except Exception:
		cc = "+91"
	return "+" + re.sub(r"\D", "", cc)


def normalize(raw, cc=None):
	if not raw:
		return None
	raw = str(raw).strip()
	digits = re.sub(r"\D", "", raw)
	if len(digits) < 7:
		return None
	cc = cc or default_cc()
	ccd = cc[1:]
	if raw.startswith("+"):
		return "+" + digits
	if digits.startswith("00"):
		return "+" + digits[2:]
	if ccd == "91":
		if len(digits) == 10:
			return "+91" + digits
		if len(digits) == 11 and digits.startswith("0"):
			return "+91" + digits[1:]
		if len(digits) == 12 and digits.startswith("91"):
			return "+" + digits
		if len(digits) == 13 and digits.startswith("091"):
			return "+" + digits[1:]
		return "+" + digits if len(digits) > 12 else "+91" + digits.lstrip("0")
	if digits.startswith(ccd) and len(digits) > 10:
		return "+" + digits
	return cc + digits.lstrip("0")


def last10(e164):
	d = re.sub(r"\D", "", e164 or "")
	return d[-10:] if len(d) >= 10 else d

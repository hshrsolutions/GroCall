"""Where recordings live on disk (grocall-prd.md §5.4).

<site>/private/files/grocall/YYYY/MM/<call>.<ext>. They are inside private/files so
`bench backup --with-files` includes them, but no File document points at them, so
Frappe's /private/files URL refuses them (it requires a File doc). The only way to
hear one is grocall.api.app.recording, which checks access and writes CL Playback Log."""

import os

import frappe

ROOT = "grocall"
PARTIAL = "_partial"
AUDIO_TYPES = {"m4a": "audio/mp4", "mp4": "audio/mp4", "aac": "audio/aac", "mp3": "audio/mpeg", "amr": "audio/amr",
	"awb": "audio/amr-wb", "3gp": "audio/3gpp", "wav": "audio/wav", "ogg": "audio/ogg", "opus": "audio/ogg",
	"flac": "audio/flac", "webm": "audio/webm"}
MAX_BYTES = 150 * 1024 * 1024
MAX_CHUNK = 8 * 1024 * 1024


def base_dir():
	return frappe.get_site_path("private", "files", ROOT)


def partial_path(call):
	d = os.path.join(base_dir(), PARTIAL)
	os.makedirs(d, exist_ok=True)
	return os.path.join(d, f"{call}.part")


def final_relpath(call, ext, when):
	return os.path.join(ROOT, f"{when:%Y}", f"{when:%m}", f"{call}.{ext}")


def abspath(relpath):
	"""Absolute path for a stored relpath, refusing anything outside the recordings folder."""
	root = os.path.realpath(base_dir())
	p = os.path.realpath(frappe.get_site_path("private", "files", relpath))
	if not p.startswith(root + os.sep):
		frappe.throw("Bad recording path", frappe.PermissionError)
	return p


def mimetype(relpath):
	return AUDIO_TYPES.get(relpath.rsplit(".", 1)[-1].lower(), "application/octet-stream")


def usage():
	total = count = 0
	for dirpath, _dirs, files in os.walk(base_dir()):
		if PARTIAL in dirpath:
			continue
		for f in files:
			total += os.path.getsize(os.path.join(dirpath, f))
			count += 1
	return {"bytes": total, "files": count}


def human(n):
	for unit in ("B", "KB", "MB", "GB", "TB"):
		if n < 1024 or unit == "TB":
			return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
		n /= 1024

// Recording player on the call form. The audio streams from grocall.api.app.recording,
// which checks access, supports seeking (HTTP Range) and logs the play.
frappe.ui.form.on("CL Call", {
	refresh(frm) {
		const wrap = frm.fields_dict.recording_status && frm.fields_dict.recording_status.$wrapper;
		if (!wrap) return;
		wrap.find(".grocall-player").remove();
		if (frm.doc.recording_status !== "Uploaded") return;
		const src = `/api/method/grocall.api.app.recording?call=${encodeURIComponent(frm.doc.name)}`;
		$(`<div class="grocall-player" style="margin-top:8px">
			<audio controls preload="none" style="width:100%" src="${src}"></audio>
			<div class="text-muted small">Every listen is recorded in the playback log.</div></div>`).appendTo(wrap);
	},
});

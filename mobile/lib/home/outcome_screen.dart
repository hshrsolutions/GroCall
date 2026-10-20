import 'package:flutter/material.dart';

import '../api.dart';
import '../models.dart';
import '../native.dart';
import 'data.dart';

/// "How did the call go?" — outcome, note, next follow-up. Opened from the after-call notification.
class OutcomeScreen extends StatefulWidget {
  const OutcomeScreen({super.key, required this.call, required this.data});
  final CallRow call;
  final AppData data;
  @override
  State<OutcomeScreen> createState() => _OutcomeScreenState();
}

class _OutcomeScreenState extends State<OutcomeScreen> {
  String? outcome;
  DateTime? followUp;
  final notes = TextEditingController();
  bool busy = false;

  void _pick(Map<String, dynamic> d) {
    setState(() {
      outcome = d['label'] as String;
      if (d['needs_follow_up'] == 1 || d['needs_follow_up'] == true) {
        final days = ((d['default_follow_up_days'] ?? 1) as num).toInt();
        final t = DateTime.now().add(Duration(days: days == 0 ? 1 : days));
        followUp = DateTime(t.year, t.month, t.day, 10);
      } else {
        followUp = null;
      }
    });
  }

  Future<void> _when() async {
    final now = DateTime.now();
    final d = await showDatePicker(context: context, firstDate: now, lastDate: now.add(const Duration(days: 365)),
        initialDate: followUp ?? now.add(const Duration(days: 1)));
    if (d == null || !mounted) return;
    final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(followUp ?? DateTime(0, 1, 1, 10)));
    setState(() => followUp = DateTime(d.year, d.month, d.day, t?.hour ?? 10, t?.minute ?? 0));
  }

  Future<void> _save() async {
    final key = widget.call.callKey;
    if (key == null) {
      await Native.syncNow();
      _snack('This call is still syncing. Try again in a few seconds.');
      return;
    }
    setState(() => busy = true);
    try {
      await Api.disposition(key, outcome!, notes.text.trim(), followUp);
      await Native.setOutcome(widget.call.id, outcome!);
      await widget.data.load();
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      _snack(e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext context) {
    final c = widget.call;
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Call outcome')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Text(c.who, style: t.titleLarge),
        Text('${c.direction} · ${fmtTime(c.startedAt)}${c.duration > 0 ? ' · ${fmtDuration(c.duration)}' : ''}', style: t.bodyMedium),
        if (c.leadName != null) Text(c.number, style: t.bodySmall),
        const SizedBox(height: 20),
        Text('What happened?', style: t.titleSmall),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final d in widget.data.dispositions)
            ChoiceChip(label: Text(d['label'] as String), selected: outcome == d['label'], onSelected: (_) => _pick(d)),
        ]),
        if (widget.data.dispositions.isEmpty) const Text('Outcomes load on the first sync. Pull down on Today to sync.'),
        const SizedBox(height: 20),
        TextField(controller: notes, maxLines: 3, decoration: const InputDecoration(labelText: 'Note (optional)', border: OutlineInputBorder())),
        const SizedBox(height: 16),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.event),
          title: Text(followUp == null ? 'No follow-up' : 'Follow up ${fmtTime(followUp!)}'),
          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
            if (followUp != null) IconButton(onPressed: () => setState(() => followUp = null), icon: const Icon(Icons.close)),
            TextButton(onPressed: _when, child: const Text('Set')),
          ]),
        ),
        const SizedBox(height: 16),
        FilledButton(onPressed: outcome == null || busy ? null : _save, child: Text(busy ? 'Saving…' : 'Save')),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: () => Native.dial(c.number), icon: const Icon(Icons.call), label: const Text('Call back')),
      ]),
    );
  }
}

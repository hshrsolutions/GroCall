import 'package:flutter/material.dart';

import '../models.dart';

class CallTile extends StatelessWidget {
  const CallTile({super.key, required this.c, required this.onTap});
  final CallRow c;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return ListTile(
      onTap: onTap,
      leading: CircleAvatar(backgroundColor: c.color(cs).withValues(alpha: .12), child: Icon(c.icon, color: c.color(cs), size: 20)),
      title: Text(c.who, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text([
        fmtTime(c.startedAt),
        if (c.duration > 0) fmtDuration(c.duration),
        c.outcome ?? (c.needsOutcome ? 'Add outcome' : c.syncLabel),
      ].join(' · ')),
      trailing: c.needsOutcome ? Icon(Icons.edit_note, color: cs.primary) : null,
    );
  }
}

class Kpi extends StatelessWidget {
  const Kpi(this.label, this.value, {super.key, this.alert = false});
  final String label, value;
  final bool alert;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label.toUpperCase(), style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: cs.onSurfaceVariant)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: alert ? cs.error : null)),
        ]),
      ),
    );
  }
}

class Empty extends StatelessWidget {
  const Empty(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Center(child: Text(text, textAlign: TextAlign.center, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant))),
      );
}

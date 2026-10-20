import 'package:flutter/material.dart';

import '../models.dart';
import '../native.dart';
import '../setup/permissions_step.dart';
import 'data.dart';
import 'outcome_screen.dart';
import 'widgets.dart';

Future<void> openCall(BuildContext context, AppData data, CallRow c) =>
    Navigator.push(context, MaterialPageRoute(builder: (_) => OutcomeScreen(call: c, data: data)));

class TodayTab extends StatelessWidget {
  const TodayTab({super.key, required this.data});
  final AppData data;
  @override
  Widget build(BuildContext context) {
    final today = data.today;
    final talk = today.fold<int>(0, (s, c) => s + (c.connected ? c.duration : 0));
    final todo = data.calls.where((c) => c.needsOutcome && c.syncState == 'sent').take(10).toList();
    final missed = data.missedOpen;
    final name = '${data.state['full_name'] ?? ''}'.split(' ').first;
    return RefreshIndicator(
      onRefresh: data.sync,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Hello${name.isEmpty ? '' : ', $name'}', style: Theme.of(context).textTheme.headlineSmall),
        Text('${data.state['sim_label'] ?? ''} · synced ${ago(((data.state['last_sync'] ?? 0) as num).toInt())}'),
        if (data.state['last_error'] != null && '${data.state['last_error']}' != 'null')
          Padding(padding: const EdgeInsets.only(top: 6),
              child: Text('Last sync problem: ${data.state['last_error']}', style: TextStyle(color: Theme.of(context).colorScheme.error))),
        const SizedBox(height: 12),
        GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), childAspectRatio: 1.9,
            children: [
              Kpi('Calls today', '${today.length}'),
              Kpi('Talk time', fmtDuration(talk)),
              Kpi('Missed, not returned', '${missed.length}', alert: missed.isNotEmpty),
              Kpi('Need an outcome', '${todo.length}', alert: todo.isNotEmpty),
            ]),
        if (missed.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('Call these back', style: Theme.of(context).textTheme.titleMedium),
          for (final c in missed.take(5))
            ListTile(
              leading: const Icon(Icons.call_missed, color: Colors.red),
              title: Text(c.who),
              subtitle: Text(fmtTime(c.startedAt)),
              trailing: IconButton.filledTonal(onPressed: () => Native.dial(c.number), icon: const Icon(Icons.call)),
            ),
        ],
        if (todo.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('Add the outcome', style: Theme.of(context).textTheme.titleMedium),
          for (final c in todo) CallTile(c: c, onTap: () => openCall(context, data, c)),
        ],
        if (today.isEmpty && missed.isEmpty && todo.isEmpty)
          const Empty('No company-SIM calls yet today.\nCalls appear here a few seconds after they end.'),
      ]),
    );
  }
}

class CallsTab extends StatefulWidget {
  const CallsTab({super.key, required this.data});
  final AppData data;
  @override
  State<CallsTab> createState() => _CallsTabState();
}

class _CallsTabState extends State<CallsTab> {
  String filter = 'all';
  @override
  Widget build(BuildContext context) {
    final rows = widget.data.calls.where((c) => switch (filter) {
          'missed' => c.direction == 'missed',
          'todo' => c.needsOutcome,
          _ => true,
        }).toList();
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'all', label: Text('All')),
            ButtonSegment(value: 'todo', label: Text('No outcome')),
            ButtonSegment(value: 'missed', label: Text('Missed')),
          ],
          selected: {filter},
          onSelectionChanged: (s) => setState(() => filter = s.first),
        ),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: widget.data.sync,
          child: rows.isEmpty
              ? ListView(children: const [Empty('No calls here.')])
              : ListView.separated(
                  itemCount: rows.length,
                  separatorBuilder: (_, _) => const Divider(height: 1),
                  itemBuilder: (_, i) => CallTile(c: rows[i], onTap: () => openCall(context, widget.data, rows[i])),
                ),
        ),
      ),
    ]);
  }
}

class LeadsTab extends StatefulWidget {
  const LeadsTab({super.key, required this.data});
  final AppData data;
  @override
  State<LeadsTab> createState() => _LeadsTabState();
}

class _LeadsTabState extends State<LeadsTab> {
  String q = '';
  @override
  Widget build(BuildContext context) {
    final rows = widget.data.leads.where((l) {
      final s = '${l['lead_name']} ${l['company_name'] ?? ''} ${(l['phones'] as List?)?.join(' ')}'.toLowerCase();
      return q.isEmpty || s.contains(q.toLowerCase());
    }).toList();
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextField(
          decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search leads', border: OutlineInputBorder()),
          onChanged: (v) => setState(() => q = v),
        ),
      ),
      Expanded(
        child: rows.isEmpty
            ? const Empty('No leads yet. Leads assigned to you in GroCall appear here, and their names show on your calls.')
            : ListView.separated(
                itemCount: rows.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (_, i) {
                  final l = rows[i];
                  final phones = (l['phones'] as List?) ?? [];
                  return ListTile(
                    title: Text('${l['lead_name']}'),
                    subtitle: Text([l['company_name'], l['stage'], phones.isEmpty ? null : phones.first]
                        .where((x) => x != null && '$x'.isNotEmpty)
                        .join(' · ')),
                    trailing: phones.isEmpty ? null : IconButton(onPressed: () => Native.dial('${phones.first}'), icon: const Icon(Icons.call)),
                  );
                },
              ),
      ),
    ]);
  }
}

class FollowUpsTab extends StatelessWidget {
  const FollowUpsTab({super.key, required this.data});
  final AppData data;
  @override
  Widget build(BuildContext context) {
    final due = data.leads.where((l) => parseServer(l['next_follow_up'] as String?) != null).toList()
      ..sort((a, b) => parseServer(a['next_follow_up'] as String?)!.compareTo(parseServer(b['next_follow_up'] as String?)!));
    final now = DateTime.now();
    return RefreshIndicator(
      onRefresh: data.sync,
      child: due.isEmpty
          ? ListView(children: const [Empty('No follow-ups. When you set one on a call outcome it appears here.')])
          : ListView.separated(
              itemCount: due.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final l = due[i];
                final when = parseServer(l['next_follow_up'] as String?)!;
                final late = when.isBefore(now);
                final phones = (l['phones'] as List?) ?? [];
                return ListTile(
                  leading: Icon(late ? Icons.warning_amber : Icons.event, color: late ? Theme.of(context).colorScheme.error : null),
                  title: Text('${l['lead_name']}'),
                  subtitle: Text('${late ? 'Overdue · ' : ''}${fmtTime(when)}${l['stage'] != null ? ' · ${l['stage']}' : ''}'),
                  trailing: phones.isEmpty ? null : IconButton.filledTonal(onPressed: () => Native.dial('${phones.first}'), icon: const Icon(Icons.call)),
                );
              },
            ),
    );
  }
}

class PhoneTab extends StatefulWidget {
  const PhoneTab({super.key, required this.data, required this.onUnpaired});
  final AppData data;
  final VoidCallback onUnpaired;
  @override
  State<PhoneTab> createState() => _PhoneTabState();
}

class _PhoneTabState extends State<PhoneTab> {
  List<dynamic> folders = [];

  @override
  void initState() {
    super.initState();
    Native.probe().then((f) => mounted ? setState(() => folders = f) : null);
  }

  Future<void> _unpair() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Unpair this phone?'),
        content: const Text('Calls stop syncing. Calls not yet sent stay on the server only if they were synced.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Unpair')),
        ],
      ),
    );
    if (ok == true) {
      await Native.unpair();
      widget.onUnpaired();
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.data.state;
    final allowFallback = widget.data.settings['allow_fallback_recorder'] == true;
    final pending = widget.data.calls.where((c) => c.syncState == 'pending').length;
    final uploading = widget.data.calls.where((c) => c.recState == 'wanted' || c.recState == 'uploading').length;
    final t = Theme.of(context).textTheme;
    return RefreshIndicator(
      onRefresh: widget.data.sync,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${s['full_name'] ?? s['user']}', style: t.titleMedium),
              Text('${s['site']}'),
              const SizedBox(height: 8),
              Text('Company SIM: ${s['sim_label']}'),
              Text('Phone ${s['device']} · Tier ${s['tier']} · app ${s['version']}'),
              Text('Last sync ${ago(((s['last_sync'] ?? 0) as num).toInt())} · $pending waiting · $uploading recordings to upload'),
              if (s['last_error'] != null && '${s['last_error']}' != 'null')
                Text('Problem: ${s['last_error']}', style: TextStyle(color: Theme.of(context).colorScheme.error)),
              const SizedBox(height: 8),
              FilledButton.tonalIcon(onPressed: widget.data.sync, icon: const Icon(Icons.sync), label: const Text('Sync now')),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        Text('Permissions', style: t.titleMedium),
        PermissionList(allowFallback: allowFallback),
        if (s['tier'] == 'B' && allowFallback)
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Fallback recorder'),
            subtitle: Text(s['fallback_running'] == true
                ? 'Accessibility service running. Records the microphone during company-SIM calls.'
                : 'Turn on "GroCall recorder" in Accessibility first.'),
            value: s['fallback'] == true,
            onChanged: (v) async {
              await Native.setFallback(v);
              await widget.data.load();
            },
          ),
        const SizedBox(height: 12),
        Text('Where this phone saves recordings', style: t.titleMedium),
        Text('Dialer: ${s['dialer']}', style: t.bodySmall),
        for (final f in folders)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(f['exists'] == true ? Icons.folder : Icons.folder_off_outlined),
            title: Text('${f['folder']}'),
            subtitle: Text(f['files'] == -1 ? 'Allow "All files access" to check' : '${f['files']} audio files'),
          ),
        const SizedBox(height: 24),
        OutlinedButton.icon(onPressed: _unpair, icon: const Icon(Icons.link_off), label: const Text('Unpair this phone')),
      ]),
    );
  }
}

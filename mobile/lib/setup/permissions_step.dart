import 'package:flutter/material.dart';

import '../native.dart';

/// One row per permission with a button that fixes it. Used in setup and in the Phone tab.
class PermissionList extends StatefulWidget {
  const PermissionList({super.key, this.allowFallback = false, this.onChanged});
  final bool allowFallback;
  final ValueChanged<Map<String, dynamic>>? onChanged;
  @override
  State<PermissionList> createState() => PermissionListState();
}

class PermissionListState extends State<PermissionList> with WidgetsBindingObserver {
  Map<String, dynamic> p = {};
  String tier = 'A';

  static const _items = [
    ('call_log', 'Call log', 'Reads company-SIM calls (required)', true),
    ('phone', 'Phone & SIM', 'Tells the company SIM from your personal one (required)', true),
    ('notifications', 'Notifications', 'Asks for the outcome after a call; missed-call reminders', true),
    ('audio', 'Audio files', 'Finds the recording your phone made', true),
    ('all_files', 'All files access', 'Needed on some phones whose recordings are hidden from apps', false),
    ('battery', 'No battery limits', 'So calls sync on time in the background', false),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    refresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) refresh(); // back from a Settings screen
  }

  Future<void> refresh() async {
    final r = await Native.permissions();
    final st = await Native.state();
    if (!mounted) return;
    setState(() {
      p = r;
      tier = '${st['tier']}';
    });
    widget.onChanged?.call(r);
  }

  Future<void> fix(String key) async {
    if (key == 'all_files' || key == 'battery' || key == 'accessibility') {
      await Native.openSettings(key);
    } else {
      final ok = await Native.requestPermission(key);
      if (!ok) await Native.openSettings('app'); // denied twice: Android only allows it from Settings now
    }
    await refresh();
  }

  @override
  Widget build(BuildContext context) {
    final rows = [
      ..._items,
      if (tier == 'B' && widget.allowFallback) ...[
        ('microphone', 'Microphone', 'Fallback recorder for this phone (optional)', false),
        ('accessibility', 'Accessibility: GroCall recorder', 'Lets the fallback recorder run during calls (optional)', false),
      ],
    ];
    return Column(children: [
      for (final (key, title, why, required) in rows)
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(p[key] == true ? Icons.check_circle : (required ? Icons.error : Icons.radio_button_unchecked),
              color: p[key] == true ? Colors.green : (required ? Theme.of(context).colorScheme.error : null)),
          title: Text(title),
          subtitle: Text(why),
          trailing: p[key] == true ? null : TextButton(onPressed: () => fix(key), child: const Text('Allow')),
        ),
    ]);
  }
}

class PermissionsStep extends StatefulWidget {
  const PermissionsStep({super.key, required this.onNext, this.allowFallback = false});
  final VoidCallback onNext;
  final bool allowFallback;
  @override
  State<PermissionsStep> createState() => _PermissionsStepState();
}

class _PermissionsStepState extends State<PermissionsStep> {
  Map<String, dynamic> p = {};
  @override
  Widget build(BuildContext context) {
    final ready = p['call_log'] == true && p['phone'] == true;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('GroCall needs these to work. Required ones are marked red until allowed.',
          style: Theme.of(context).textTheme.bodyLarge),
      const SizedBox(height: 8),
      PermissionList(allowFallback: widget.allowFallback, onChanged: (r) => setState(() => p = r)),
      const SizedBox(height: 16),
      FilledButton(onPressed: ready ? widget.onNext : null, child: const Text('Continue')),
    ]);
  }
}

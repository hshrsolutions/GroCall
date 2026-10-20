import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../api.dart';
import '../native.dart';
import 'permissions_step.dart';

/// First run: scan the pairing QR → read the notice → pick the company SIM → pair →
/// permissions → turn on the phone's own call recording. Ends by calling [onDone].
class SetupFlow extends StatefulWidget {
  const SetupFlow({super.key, required this.onDone});
  final VoidCallback onDone;
  @override
  State<SetupFlow> createState() => _SetupFlowState();
}

class _SetupFlowState extends State<SetupFlow> {
  int step = 0; // 0 code, 1 notice, 2 SIM, 3 permissions, 4 recorder guide
  String site = '', code = '';
  Map<String, dynamic> settings = {};
  List<dynamic> sims = [];
  String? simId;
  bool busy = false;
  String? error;
  final siteCtl = TextEditingController(text: 'https://');
  final codeCtl = TextEditingController();

  Future<void> _useQr(String raw) async {
    try {
      final j = jsonDecode(raw) as Map<String, dynamic>;
      if (j['app'] != 'grocall') throw const FormatException();
      siteCtl.text = j['site'] as String;
      codeCtl.text = j['code'] as String;
      await _next0();
    } catch (_) {
      setState(() => error = 'That QR code is not a GroCall pairing code.');
    }
  }

  Future<void> _next0() async {
    site = siteCtl.text.trim();
    code = codeCtl.text.trim().toUpperCase().replaceAll(RegExp(r'[\s-]'), '');
    if (!site.startsWith('https://') || code.length != 8) {
      setState(() => error = 'Enter the site address (https://…) and the 8-character code.');
      return;
    }
    await _run(() async {
      settings = ((await Api.consent(site))['settings'] as Map).cast<String, dynamic>();
      setState(() => step = 1);
    });
  }

  Future<void> _accept() async {
    await _run(() async {
      await Native.requestPermission('phone');
      sims = await Native.sims();
      if (sims.length == 1) simId = sims.first['subscription_id'] as String;
      setState(() => step = 2);
    });
  }

  Future<void> _pair() async {
    final sim = sims.firstWhere((s) => s['subscription_id'] == simId) as Map<String, dynamic>;
    await _run(() async {
      final info = await Native.deviceInfo();
      info['sim'] = {
        'subscription_id': sim['subscription_id'],
        'carrier': sim['carrier'],
        'last4': sim['last4'],
        'fingerprint': sim['fingerprint'],
      };
      final r = await Api.pair(site, code, info);
      await Native.savePairing({
        'site': site,
        'device': r['device'],
        'key': r['key'],
        'user': r['user'],
        'full_name': r['full_name'],
        'sim_sub_id': sim['subscription_id'],
        'sim_label': 'SIM ${sim['slot']} · ${sim['carrier']}${(sim['last4'] as String).isEmpty ? '' : ' ···${sim['last4']}'}',
        'cache': jsonEncode({'settings': r['settings'], 'recorder_profiles': r['recorder_profiles']}),
      });
      setState(() => step = 3);
    });
  }

  Future<void> _run(Future<void> Function() f) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await f();
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final body = switch (step) {
      0 => _codeStep(t),
      1 => _noticeStep(t),
      2 => _simStep(t),
      3 => PermissionsStep(onNext: () => setState(() => step = 4), allowFallback: settings['allow_fallback_recorder'] == true),
      _ => RecorderGuide(onDone: widget.onDone),
    };
    return Scaffold(
      appBar: AppBar(title: Text(['Pair this phone', 'Before you start', 'Company SIM', 'Permissions', 'Call recording'][step])),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(20), children: [
          LinearProgressIndicator(value: (step + 1) / 5),
          const SizedBox(height: 20),
          body,
          if (error != null) Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        ]),
      ),
    );
  }

  Widget _codeStep(TextTheme t) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Scan the pairing code your manager shows in GroCall → Phones.', style: t.bodyLarge),
        const SizedBox(height: 16),
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: SizedBox(
            height: 260,
            child: MobileScanner(onDetect: (cap) {
              final raw = cap.barcodes.isEmpty ? null : cap.barcodes.first.rawValue;
              if (raw != null && !busy && step == 0) _useQr(raw);
            }),
          ),
        ),
        const SizedBox(height: 20),
        Text('Or type it', style: t.titleSmall),
        const SizedBox(height: 8),
        TextField(controller: siteCtl, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Site address')),
        const SizedBox(height: 8),
        TextField(controller: codeCtl, textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(labelText: 'Pairing code (8 characters)')),
        const SizedBox(height: 16),
        FilledButton(onPressed: busy ? null : _next0, child: Text(busy ? 'Checking…' : 'Continue')),
      ]);

  Widget _noticeStep(TextTheme t) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Card(child: Padding(padding: const EdgeInsets.all(16), child: Text('${settings['consent_text'] ?? ''}', style: t.bodyLarge))),
        const SizedBox(height: 12),
        Text('Only calls on the company SIM you choose next are tracked. Your personal SIM is never read or sent.',
            style: t.bodyMedium),
        if ((settings['customer_announcement'] ?? '') != '') ...[
          const SizedBox(height: 12),
          Text('Tell customers: “${settings['customer_announcement']}”', style: t.bodyMedium?.copyWith(fontStyle: FontStyle.italic)),
        ],
        const SizedBox(height: 20),
        FilledButton(onPressed: busy ? null : _accept, child: const Text('I understand and agree')),
        TextButton(onPressed: () => setState(() => step = 0), child: const Text('Back')),
      ]);

  Widget _simStep(TextTheme t) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Which SIM is the company SIM?', style: t.titleMedium),
        const SizedBox(height: 8),
        if (sims.isEmpty)
          const Text('No SIM found. Allow the Phone permission (Settings → Apps → GroCall → Permissions) and try again.'),
        RadioGroup<String>(
          groupValue: simId,
          onChanged: (v) => setState(() => simId = v),
          child: Column(children: [
            for (final s in sims)
              RadioListTile<String>(
                value: s['subscription_id'] as String,
                title: Text('SIM ${s['slot']} · ${s['carrier']}'),
                subtitle: Text((s['last4'] as String).isEmpty ? (s['display_name'] as String) : 'Number ending ${s['last4']}'),
              ),
          ]),
        ),
        const SizedBox(height: 16),
        FilledButton(onPressed: busy || simId == null ? null : _pair, child: Text(busy ? 'Pairing…' : 'Pair this phone')),
        if (sims.isEmpty) TextButton(onPressed: _accept, child: const Text('Look again')),
      ]);
}

/// Last step: the phone's own dialer must record calls automatically; show where that switch is.
class RecorderGuide extends StatelessWidget {
  const RecorderGuide({super.key, required this.onDone});
  final VoidCallback onDone;

  static String steps(String brand, String tier) {
    if (tier == 'B') {
      return 'This phone uses the Google Phone app, which keeps call recordings private. Calls, outcomes and '
          'follow-ups are tracked normally. If your company allows it, turn on the GroCall fallback recorder in '
          'the Phone tab (it records the microphone, best effort).';
    }
    return switch (brand) {
      'samsung' => 'Phone app → ⋮ → Settings → Record calls → turn on "Auto record calls" → "All calls" '
          '(or "Calls with unsaved numbers" + your contacts).',
      'xiaomi' || 'redmi' || 'poco' => 'Phone app → ⋮ / Settings → Call recording → turn on "Record calls automatically" → All numbers.',
      'oppo' || 'realme' || 'oneplus' => 'Phone app → ⋮ → Settings → Call recording → turn on "Auto call recording" → All calls.',
      'vivo' || 'iqoo' => 'Phone app → Settings → Call recording → turn on "Auto record calls" → All calls.',
      _ => 'Open your Phone app → Settings → Call recording, and turn on automatic recording of all calls.',
    };
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
        future: Native.deviceInfo(),
        builder: (context, snap) {
          final d = snap.data ?? {};
          final t = Theme.of(context).textTheme;
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Turn on automatic call recording', style: t.titleMedium),
            const SizedBox(height: 8),
            Text(steps('${d['brand'] ?? ''}', '${d['support_tier'] ?? 'A'}'), style: t.bodyLarge),
            const SizedBox(height: 16),
            OutlinedButton.icon(onPressed: Native.openDialer, icon: const Icon(Icons.dialpad), label: const Text('Open the Phone app')),
            const SizedBox(height: 8),
            FilledButton(onPressed: onDone, child: const Text('Done — start tracking')),
          ]);
        },
      );
}

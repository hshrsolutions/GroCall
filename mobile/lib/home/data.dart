import 'package:flutter/foundation.dart';

import '../models.dart';
import '../native.dart';

/// What the screens show: local company-SIM calls plus the last server pull.
class AppData extends ChangeNotifier {
  List<CallRow> calls = [];
  Map<String, dynamic> cache = {};
  Map<String, dynamic> state = {};

  Future<void> load() async {
    calls = (await Native.calls()).map((e) => CallRow((e as Map).cast<String, dynamic>())).toList();
    cache = await Native.cache();
    state = await Native.state();
    notifyListeners();
  }

  Future<void> sync() async {
    await Native.syncNow();
    // The native worker runs in the background; reload as it finishes.
    for (final s in [3, 8, 15]) {
      await Future<void>.delayed(Duration(seconds: s == 3 ? 3 : 5));
      await load();
    }
  }

  List<Map<String, dynamic>> get leads =>
      ((cache['leads'] as List?) ?? []).map((e) => (e as Map).cast<String, dynamic>()).toList();
  List<Map<String, dynamic>> get dispositions =>
      ((cache['dispositions'] as List?) ?? []).map((e) => (e as Map).cast<String, dynamic>()).toList();
  Map<String, dynamic> get settings => ((cache['settings'] as Map?) ?? {}).cast<String, dynamic>();

  List<CallRow> get today {
    final n = DateTime.now();
    return calls.where((c) => c.startedAt.year == n.year && c.startedAt.month == n.month && c.startedAt.day == n.day).toList();
  }

  /// A missed call counts as returned once any later call to/from that number connects.
  bool returned(CallRow missed) {
    final tail = _tail(missed.number);
    return calls.any((c) => c.startedAt.isAfter(missed.startedAt) && c.connected && _tail(c.number) == tail);
  }

  List<CallRow> get missedOpen => calls
      .where((c) => c.direction == 'missed' && DateTime.now().difference(c.startedAt).inDays < 3 && !returned(c))
      .toList();

  String _tail(String n) {
    final d = n.replaceAll(RegExp(r'\D'), '');
    return d.length > 10 ? d.substring(d.length - 10) : d;
  }

  String? leadNameFor(String number) {
    final tail = _tail(number);
    for (final l in leads) {
      for (final p in (l['phones'] as List? ?? [])) {
        if (_tail('$p') == tail) return l['lead_name'] as String?;
      }
    }
    return null;
  }
}

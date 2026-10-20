import 'package:flutter/material.dart';

class CallRow {
  CallRow(this.j);
  final Map<String, dynamic> j;

  int get id => (j['id'] as num).toInt();
  String get number => (j['number'] ?? '') as String;
  String get direction => (j['direction'] ?? '') as String;
  DateTime get startedAt => DateTime.fromMillisecondsSinceEpoch((j['started_at'] as num).toInt());
  int get duration => ((j['duration'] ?? 0) as num).toInt();
  String get syncState => (j['sync_state'] ?? '') as String;
  String? get callKey => _s('call_key');
  String? get leadName => _s('lead_name');
  String get recState => (j['rec_state'] ?? 'none') as String;
  String? get outcome => _s('outcome');
  String get who => leadName ?? (number.isEmpty ? 'Unknown number' : number);
  bool get connected => (direction == 'incoming' || direction == 'outgoing') && duration > 0;
  bool get needsOutcome => connected && outcome == null;

  String? _s(String k) {
    final v = j[k];
    return (v == null || v is! String || v.isEmpty || v == 'null') ? null : v;
  }

  IconData get icon => switch (direction) {
        'incoming' => Icons.call_received,
        'outgoing' => Icons.call_made,
        'missed' => Icons.call_missed,
        'rejected' => Icons.call_end,
        _ => Icons.block,
      };

  Color color(ColorScheme c) => direction == 'missed' || direction == 'rejected' ? c.error : c.primary;

  String get syncLabel => switch (syncState) {
        'pending' => 'Waiting to sync',
        'excluded' => 'Not tracked',
        _ => switch (recState) {
            'wanted' || 'uploading' => 'Recording uploading',
            'done' => 'Recording saved',
            'missing' => 'No recording',
            _ => 'Synced',
          },
      };
}

String fmtDuration(int s) => s < 60 ? '${s}s' : '${s ~/ 60}m ${s % 60}s';

String fmtTime(DateTime d) {
  final now = DateTime.now();
  final hm = '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  if (d.year == now.year && d.month == now.month && d.day == now.day) return hm;
  const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return '${d.day} ${m[d.month - 1]} $hm';
}

String ago(int ms) {
  if (ms <= 0) return 'never';
  final m = DateTime.now().difference(DateTime.fromMillisecondsSinceEpoch(ms)).inMinutes;
  if (m < 1) return 'just now';
  if (m < 60) return '$m min ago';
  if (m < 1440) return '${m ~/ 60} h ago';
  return '${m ~/ 1440} d ago';
}

DateTime? parseServer(String? s) => (s == null || s.isEmpty) ? null : DateTime.tryParse(s.replaceFirst(' ', 'T'));

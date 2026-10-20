import 'package:flutter_test/flutter_test.dart';
import 'package:grocall/models.dart';
import 'package:grocall/setup/setup_flow.dart';

void main() {
  test('call row basics', () {
    final c = CallRow({'id': 1, 'number': '09876543210', 'direction': 'outgoing', 'started_at': 0, 'duration': 75,
      'sync_state': 'sent', 'rec_state': 'done', 'lead_name': null, 'outcome': null});
    expect(c.connected, true);
    expect(c.needsOutcome, true);
    expect(c.who, '09876543210');
    expect(c.syncLabel, 'Recording saved');
    expect(fmtDuration(75), '1m 15s');
  });

  test('missed call needs no outcome', () {
    final c = CallRow({'id': 2, 'number': '1', 'direction': 'missed', 'started_at': 0, 'duration': 0, 'lead_name': 'Ravi'});
    expect(c.needsOutcome, false);
    expect(c.who, 'Ravi');
  });

  test('recorder guide per brand', () {
    expect(RecorderGuide.steps('samsung', 'A'), contains('Auto record calls'));
    expect(RecorderGuide.steps('pixel', 'B'), contains('Google Phone'));
  });
}

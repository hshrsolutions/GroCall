import 'dart:convert';

import 'package:http/http.dart' as http;

import 'native.dart';

class ApiError implements Exception {
  ApiError(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}

/// Interactive server calls from the UI (docs/DEVICE-API.md). Background sync is native.
class Api {
  static Future<Map<String, dynamic>> _post(String site, String method, Map<String, dynamic> body,
      {Map<String, String> headers = const {}}) async {
    final uri = Uri.parse('${site.replaceAll(RegExp(r'/+$'), '')}/api/method/grocall.api.device.$method');
    http.Response r;
    try {
      r = await http
          .post(uri, headers: {'Content-Type': 'application/json', 'Accept': 'application/json', ...headers},
              body: jsonEncode(body))
          .timeout(const Duration(seconds: 25));
    } catch (e) {
      throw ApiError(0, 'No connection to $site. Check the internet and try again.');
    }
    Map<String, dynamic> j = {};
    try {
      j = jsonDecode(r.body) as Map<String, dynamic>;
    } catch (_) {}
    if (r.statusCode < 200 || r.statusCode > 299) throw ApiError(r.statusCode, _message(j) ?? 'Server error ${r.statusCode}');
    return (j['message'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  static String? _message(Map<String, dynamic> j) {
    try {
      final list = jsonDecode(j['_server_messages'] as String) as List;
      final first = jsonDecode(list.first as String) as Map;
      return (first['message'] as String).replaceAll(RegExp(r'<[^>]+>'), '');
    } catch (_) {}
    if (r'' != (j['exception'] ?? '')) return (j['exception'] as String).split(':').skip(1).join(':').trim();
    if (j['exc_type'] == 'RateLimitExceededError') return 'Too many attempts. Wait a few minutes.';
    return null;
  }

  static Future<Map<String, dynamic>> consent(String site) => _post(site, 'consent', {});

  static Future<Map<String, dynamic>> pair(String site, String code, Map<String, dynamic> deviceInfo) =>
      _post(site, 'pair', {'code': code, 'consent_accepted': true, 'device_info': deviceInfo});

  static Future<Map<String, dynamic>> authed(String method, Map<String, dynamic> body) async {
    final c = await Native.credentials();
    return _post(c['site'] as String, method, body,
        headers: {'X-GroCall-Device': c['device'] as String, 'X-GroCall-Key': c['key'] as String});
  }

  static Future<Map<String, dynamic>> disposition(String callKey, String outcome, String notes, DateTime? followUp) =>
      authed('disposition', {
        'call_key': callKey,
        'disposition': outcome,
        'notes': notes,
        if (followUp != null) 'next_follow_up': fmtServer(followUp),
      });

  static String fmtServer(DateTime d) =>
      '${d.year}-${_pad2(d.month)}-${_pad2(d.day)} ${_pad2(d.hour)}:${_pad2(d.minute)}:00';
  static String _pad2(int n) => n.toString().padLeft(2, '0');
}

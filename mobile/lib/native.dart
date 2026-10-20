import 'dart:convert';

import 'package:flutter/services.dart';

/// Bridge to the Kotlin side (MainActivity.kt). Everything that touches the phone — call log,
/// SIMs, recordings, the encrypted device key, background sync — lives there.
class Native {
  static const _ch = MethodChannel('grocall/native');

  static Future<Map<String, dynamic>> _json(String m, [Map<String, dynamic>? a]) async =>
      jsonDecode(await _ch.invokeMethod<String>(m, a) ?? '{}') as Map<String, dynamic>;
  static Future<List<dynamic>> _list(String m, [Map<String, dynamic>? a]) async =>
      jsonDecode(await _ch.invokeMethod<String>(m, a) ?? '[]') as List<dynamic>;

  static Future<Map<String, dynamic>> state() => _json('state');
  static Future<Map<String, dynamic>> deviceInfo() => _json('deviceInfo');
  static Future<List<dynamic>> sims() => _list('sims');
  static Future<Map<String, dynamic>> credentials() => _json('credentials');
  static Future<Map<String, dynamic>> cache() => _json('cache');
  static Future<List<dynamic>> calls({int limit = 300}) => _list('calls', {'limit': limit});
  static Future<Map<String, dynamic>> permissions() => _json('permissions');
  static Future<List<dynamic>> probe() => _list('probe');

  static Future<bool> requestPermission(String name) async =>
      await _ch.invokeMethod<bool>('requestPermission', {'name': name}) ?? false;
  static Future<void> openSettings(String kind) => _ch.invokeMethod('openSettings', {'kind': kind});
  static Future<void> savePairing(Map<String, dynamic> p) => _ch.invokeMethod('savePairing', p);
  static Future<void> unpair() => _ch.invokeMethod('unpair');
  static Future<void> syncNow() => _ch.invokeMethod('syncNow');
  static Future<void> setOutcome(int id, String outcome) => _ch.invokeMethod('setOutcome', {'id': id, 'outcome': outcome});
  static Future<void> setFallback(bool on) => _ch.invokeMethod('setFallback', {'on': on});
  static Future<void> dial(String number) => _ch.invokeMethod('dial', {'number': number});
  static Future<String?> openDialer() => _ch.invokeMethod<String>('openDialer');
  static Future<int> launchCall() async => (await _ch.invokeMethod<num>('launchCall') ?? -1).toInt();

  /// Called when a notification is tapped while the app is already open.
  static void onOpenCall(void Function(int id) handler) {
    _ch.setMethodCallHandler((call) async {
      if (call.method == 'openCall') handler((call.arguments as num).toInt());
    });
  }
}

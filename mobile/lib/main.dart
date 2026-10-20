import 'package:flutter/material.dart';

import 'home/data.dart';
import 'home/tabs.dart';
import 'native.dart';
import 'setup/setup_flow.dart';

void main() => runApp(const GroCallApp());

const brand = Color(0xFF0F766E);

class GroCallApp extends StatelessWidget {
  const GroCallApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'GroCall',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: brand), useMaterial3: true),
        darkTheme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: brand, brightness: Brightness.dark), useMaterial3: true),
        home: const Root(),
      );
}

class Root extends StatefulWidget {
  const Root({super.key});
  @override
  State<Root> createState() => _RootState();
}

class _RootState extends State<Root> {
  bool? paired;
  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final s = await Native.state();
    setState(() => paired = s['paired'] == true);
  }

  @override
  Widget build(BuildContext context) {
    if (paired == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (!paired!) return SetupFlow(onDone: _check);
    return Home(onUnpaired: _check);
  }
}

class Home extends StatefulWidget {
  const Home({super.key, required this.onUnpaired});
  final VoidCallback onUnpaired;
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> with WidgetsBindingObserver {
  final data = AppData();
  int tab = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    data.addListener(() => mounted ? setState(() {}) : null);
    Native.onOpenCall(_openLocal);
    data.load().then((_) async {
      final id = await Native.launchCall();
      if (id > 0) _openLocal(id);
    });
    data.sync();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) data.load();
  }

  Future<void> _openLocal(int id) async {
    await data.load();
    final c = data.calls.where((x) => x.id == id);
    if (c.isNotEmpty && mounted) openCall(context, data, c.first);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      TodayTab(data: data),
      CallsTab(data: data),
      LeadsTab(data: data),
      FollowUpsTab(data: data),
      PhoneTab(data: data, onUnpaired: widget.onUnpaired),
    ];
    const titles = ['Today', 'Calls', 'Leads', 'Follow-ups', 'Phone'];
    return Scaffold(
      appBar: AppBar(title: Text(titles[tab])),
      body: SafeArea(child: pages[tab]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (i) => setState(() => tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Today'),
          NavigationDestination(icon: Icon(Icons.call_outlined), selectedIcon: Icon(Icons.call), label: 'Calls'),
          NavigationDestination(icon: Icon(Icons.people_outline), selectedIcon: Icon(Icons.people), label: 'Leads'),
          NavigationDestination(icon: Icon(Icons.event_outlined), selectedIcon: Icon(Icons.event), label: 'Follow-ups'),
          NavigationDestination(icon: Icon(Icons.phone_android_outlined), selectedIcon: Icon(Icons.phone_android), label: 'Phone'),
        ],
      ),
    );
  }
}

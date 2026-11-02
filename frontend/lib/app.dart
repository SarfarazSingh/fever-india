import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'providers/bookings_provider.dart';
import 'screens/my_trips_dashboard.dart';
import 'screens/search_screen.dart';

class ConciergeApp extends StatelessWidget {
  const ConciergeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Business Class Concierge',
      debugShowCheckedModeBanner: false,
      theme: ConciergeTheme.dark(),
      home: const HomeShell(),
    );
  }
}

final homeTabProvider = StateProvider<int>((ref) => 0);

class HomeShell extends ConsumerWidget {
  const HomeShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final index = ref.watch(homeTabProvider);
    return Scaffold(
      body: IndexedStack(
        index: index,
        children: const [SearchScreen(), MyTripsDashboard()],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) {
          ref.read(homeTabProvider.notifier).state = i;
          if (i == 1) ref.read(bookingsProvider.notifier).refresh();
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.flight_takeoff_outlined),
            selectedIcon: Icon(Icons.flight_takeoff),
            label: 'Search',
          ),
          NavigationDestination(
            icon: Icon(Icons.airplane_ticket_outlined),
            selectedIcon: Icon(Icons.airplane_ticket),
            label: 'My Trips',
          ),
        ],
      ),
    );
  }
}

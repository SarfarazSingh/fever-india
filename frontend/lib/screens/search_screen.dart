import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/theme.dart';
import '../data/airports.dart';
import '../data/models/flight_offer.dart';
import '../providers/search_provider.dart';
import '../widgets/flight_card.dart';
import 'airline_booking_webview.dart';

class SearchScreen extends ConsumerWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(searchProvider);
    final notifier = ref.read(searchProvider.notifier);
    final theme = Theme.of(context);

    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('CONCIERGE',
                      style: theme.textTheme.labelMedium
                          ?.copyWith(color: ConciergeColors.gold, letterSpacing: 4, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  Text('Fly Business, book direct.', style: theme.textTheme.headlineMedium),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Stack(
                        alignment: Alignment.centerRight,
                        children: [
                          Column(
                            children: [
                              AirportField(
                                label: 'From',
                                icon: Icons.flight_takeoff,
                                value: state.origin,
                                onChanged: notifier.setOrigin,
                              ),
                              const SizedBox(height: 12),
                              AirportField(
                                label: 'To',
                                icon: Icons.flight_land,
                                value: state.destination,
                                onChanged: notifier.setDestination,
                              ),
                            ],
                          ),
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: IconButton.filledTonal(
                              tooltip: 'Swap',
                              onPressed: notifier.swap,
                              icon: const Icon(Icons.swap_vert, color: ConciergeColors.gold),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _DateField(date: state.date, onChanged: notifier.setDate),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: state.results?.isLoading == true ? null : notifier.search,
                        icon: const Icon(Icons.search),
                        label: const Text('Search Business Class'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          ..._results(context, state),
          const SliverToBoxAdapter(child: SizedBox(height: 24)),
        ],
      ),
    );
  }

  List<Widget> _results(BuildContext context, SearchState state) {
    final theme = Theme.of(context);
    final results = state.results;
    if (results == null) {
      return const [
        SliverFillRemaining(
          hasScrollBody: false,
          child: _EmptyHint(
            icon: Icons.airline_seat_flat,
            text: 'Lie-flat seats, lounge access and priority boarding.\nSearch a route to begin.',
          ),
        ),
      ];
    }
    return results.when(
      loading: () => const [
        SliverFillRemaining(hasScrollBody: false, child: Center(child: CircularProgressIndicator())),
      ],
      error: (e, _) => [
        SliverFillRemaining(hasScrollBody: false, child: _EmptyHint(icon: Icons.cloud_off, text: e.toString())),
      ],
      data: (offers) {
        if (offers.isEmpty) {
          return const [
            SliverFillRemaining(
              hasScrollBody: false,
              child: _EmptyHint(icon: Icons.event_busy, text: 'No Business Class seats found for this date.'),
            ),
          ];
        }
        return [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Row(
                children: [
                  Text('${offers.length} Business Class options', style: theme.textTheme.titleMedium),
                  const Spacer(),
                  if (state.provider == 'mock')
                    Text('Demo data',
                        style: theme.textTheme.labelSmall?.copyWith(color: ConciergeColors.textSecondary)),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverList.separated(
              itemCount: offers.length,
              separatorBuilder: (_, __) => const SizedBox(height: 14),
              itemBuilder: (context, i) => FlightCard(
                offer: offers[i],
                onBook: () => _openBooking(context, offers[i]),
              ),
            ),
          ),
        ];
      },
    );
  }

  void _openBooking(BuildContext context, FlightOffer offer) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => AirlineBookingWebView(offer: offer)),
    );
  }
}

class AirportField extends StatefulWidget {
  const AirportField({
    super.key,
    required this.label,
    required this.icon,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final IconData icon;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  State<AirportField> createState() => _AirportFieldState();
}

class _AirportFieldState extends State<AirportField> {
  late final TextEditingController _controller = TextEditingController(text: widget.value);
  final FocusNode _focus = FocusNode();

  @override
  void didUpdateWidget(AirportField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value != oldWidget.value && widget.value != _controller.text.toUpperCase()) {
      _controller.text = widget.value;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final airport = airportByIata(widget.value);
    return RawAutocomplete<Airport>(
      textEditingController: _controller,
      focusNode: _focus,
      displayStringForOption: (a) => a.iata,
      optionsBuilder: (value) => searchAirports(value.text),
      onSelected: (a) {
        widget.onChanged(a.iata);
        _focus.unfocus();
      },
      fieldViewBuilder: (context, controller, focusNode, onSubmit) => TextField(
        controller: controller,
        focusNode: focusNode,
        textCapitalization: TextCapitalization.characters,
        onChanged: (text) {
          final code = text.trim().toUpperCase();
          if (RegExp(r'^[A-Z]{3}$').hasMatch(code)) widget.onChanged(code);
        },
        onSubmitted: (_) => onSubmit(),
        decoration: InputDecoration(
          labelText: widget.label,
          prefixIcon: Icon(widget.icon),
          helperText: airport == null ? 'City or IATA code' : '${airport.city} · ${airport.name}',
        ),
      ),
      optionsViewBuilder: (context, onSelected, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          color: ConciergeColors.surfaceHigh,
          elevation: 8,
          borderRadius: BorderRadius.circular(14),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 280, maxWidth: 360),
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 6),
              shrinkWrap: true,
              children: [
                for (final a in options)
                  ListTile(
                    dense: true,
                    leading: Text(a.iata,
                        style: const TextStyle(color: ConciergeColors.gold, fontWeight: FontWeight.w700)),
                    title: Text(a.city),
                    subtitle: Text(a.name, style: const TextStyle(color: ConciergeColors.textSecondary)),
                    onTap: () => onSelected(a),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DateField extends StatelessWidget {
  const _DateField({required this.date, required this.onChanged});

  final DateTime date;
  final ValueChanged<DateTime> onChanged;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () async {
        final now = DateTime.now();
        final picked = await showDatePicker(
          context: context,
          initialDate: date.isBefore(now) ? now : date,
          firstDate: DateTime(now.year, now.month, now.day),
          lastDate: now.add(const Duration(days: 330)),
          helpText: 'Departure date',
        );
        if (picked != null) onChanged(picked);
      },
      child: InputDecorator(
        decoration: const InputDecoration(labelText: 'Departure', prefixIcon: Icon(Icons.calendar_month)),
        child: Text(DateFormat('EEEE, d MMMM yyyy').format(date)),
      ),
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 48, color: ConciergeColors.goldDark),
          const SizedBox(height: 12),
          Text(text,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: ConciergeColors.textSecondary)),
        ],
      ),
    );
  }
}

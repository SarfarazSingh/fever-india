import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/theme.dart';
import '../data/models/flight_offer.dart';

class FlightCard extends StatelessWidget {
  const FlightCard({super.key, required this.offer, required this.onBook});

  final FlightOffer offer;
  final VoidCallback onBook;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final time = DateFormat('HH:mm');
    final price = NumberFormat.simpleCurrency(name: offer.currency, decimalDigits: 0);
    final dayOffset = offer.arrivalDayOffset;

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _CarrierBadge(code: offer.airlineIata),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(offer.airlineName,
                          style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
                      Text('${offer.flightNumber}  ·  Business',
                          style: theme.textTheme.bodySmall?.copyWith(color: ConciergeColors.textSecondary)),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(price.format(offer.price),
                        style: theme.textTheme.titleLarge?.copyWith(color: ConciergeColors.gold)),
                    Text('per traveller',
                        style: theme.textTheme.labelSmall?.copyWith(color: ConciergeColors.textSecondary)),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                _TimeColumn(time: time.format(offer.departureLocal), code: offer.origin),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Column(
                      children: [
                        Text(offer.durationLabel,
                            style: theme.textTheme.labelMedium?.copyWith(color: ConciergeColors.textSecondary)),
                        const SizedBox(height: 4),
                        _RouteLine(stops: offer.layovers),
                        const SizedBox(height: 4),
                        Text(
                          offer.stopsLabel,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: offer.layovers == 0 ? ConciergeColors.success : ConciergeColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                _TimeColumn(
                  time: time.format(offer.arrivalLocal),
                  code: offer.destination,
                  suffix: dayOffset > 0 ? '+$dayOffset' : null,
                  alignEnd: true,
                ),
              ],
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onBook,
              icon: const Icon(Icons.open_in_new, size: 18),
              label: const Text('Book Direct on Airline'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CarrierBadge extends StatelessWidget {
  const _CarrierBadge({required this.code});

  final String code;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: ConciergeColors.goldGradient,
      ),
      child: Text(code,
          style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w800, letterSpacing: 0.5)),
    );
  }
}

class _TimeColumn extends StatelessWidget {
  const _TimeColumn({required this.time, required this.code, this.suffix, this.alignEnd = false});

  final String time;
  final String code;
  final String? suffix;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(time, style: theme.textTheme.headlineSmall),
            if (suffix != null)
              Padding(
                padding: const EdgeInsets.only(left: 2),
                child: Text(suffix!, style: theme.textTheme.labelSmall?.copyWith(color: ConciergeColors.gold)),
              ),
          ],
        ),
        Text(code, style: theme.textTheme.labelLarge?.copyWith(color: ConciergeColors.textSecondary)),
      ],
    );
  }
}

class _RouteLine extends StatelessWidget {
  const _RouteLine({required this.stops});

  final int stops;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 14,
      child: Row(
        children: [
          const _Dot(filled: true),
          for (var i = 0; i < stops; i++) ...[
            const Expanded(child: Divider(color: ConciergeColors.goldDark, thickness: 1.2)),
            const _Dot(filled: false),
          ],
          const Expanded(child: Divider(color: ConciergeColors.goldDark, thickness: 1.2)),
          const Icon(Icons.flight, size: 14, color: ConciergeColors.gold),
        ],
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.filled});

  final bool filled;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: filled ? ConciergeColors.gold : ConciergeColors.background,
        border: Border.all(color: ConciergeColors.gold, width: 1.2),
      ),
    );
  }
}

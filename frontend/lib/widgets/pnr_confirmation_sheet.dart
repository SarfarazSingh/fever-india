import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../data/models/booking.dart';
import '../data/models/flight_offer.dart';
import 'manual_pnr_form.dart';

/// Native sheet shown when a confirmation code is spotted in the airline page.
/// Resolves to the registered booking, or null if the traveller declines.
Future<Booking?> showPnrConfirmationSheet(
  BuildContext context, {
  required String pnr,
  FlightOffer? offer,
}) {
  return showModalBottomSheet<Booking>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => BookingDetailsForm(
      initialPnr: pnr,
      offer: offer,
      submitLabel: 'Yes, auto check-in',
      cancelLabel: 'Not now',
      header: _DetectedHeader(pnr: pnr),
    ),
  );
}

class _DetectedHeader extends StatelessWidget {
  const _DetectedHeader({required this.pnr});

  final String pnr;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 52,
          height: 52,
          decoration: const BoxDecoration(shape: BoxShape.circle, gradient: ConciergeColors.goldGradient),
          child: const Icon(Icons.auto_awesome, color: Colors.black),
        ),
        const SizedBox(height: 16),
        Text.rich(
          TextSpan(
            style: theme.textTheme.titleLarge,
            children: [
              const TextSpan(text: 'We detected your booking code '),
              TextSpan(
                text: pnr,
                style: const TextStyle(color: ConciergeColors.gold, letterSpacing: 2, fontWeight: FontWeight.w700),
              ),
              const TextSpan(text: '. Auto-check you in 24h before departure?'),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'We will check you in the moment the window opens and deliver your boarding pass to My Trips.',
          style: theme.textTheme.bodyMedium?.copyWith(color: ConciergeColors.textSecondary),
        ),
      ],
    );
  }
}

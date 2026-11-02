import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/config.dart';
import '../core/theme.dart';
import '../data/models/booking.dart';
import '../providers/bookings_provider.dart';
import '../widgets/countdown_timer.dart';
import '../widgets/manual_pnr_form.dart';
import '../widgets/status_chip.dart';
import 'boarding_pass_viewer.dart';

class MyTripsDashboard extends ConsumerStatefulWidget {
  const MyTripsDashboard({super.key});

  @override
  ConsumerState<MyTripsDashboard> createState() => _MyTripsDashboardState();
}

class _MyTripsDashboardState extends ConsumerState<MyTripsDashboard> {
  Timer? _poller;

  @override
  void initState() {
    super.initState();
    _poller = Timer.periodic(const Duration(seconds: 30), (_) {
      // IndexedStack disables tickers for hidden tabs; only poll when visible.
      if (mounted && TickerMode.of(context)) {
        ref.read(bookingsProvider.notifier).refresh();
      }
    });
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _addManual() async {
    final booking = await showManualPnrForm(context);
    if (booking != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Auto check-in scheduled for ${booking.pnrCode}.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final bookings = ref.watch(bookingsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('My Trips')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addManual,
        icon: const Icon(Icons.add),
        label: const Text('Add PNR'),
      ),
      body: RefreshIndicator(
        color: ConciergeColors.gold,
        onRefresh: () => ref.read(bookingsProvider.notifier).refresh(),
        child: bookings.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _Message(
            icon: Icons.cloud_off,
            text: e.toString(),
            action: TextButton(
              onPressed: () => ref.read(bookingsProvider.notifier).refresh(),
              child: const Text('Retry'),
            ),
          ),
          data: (list) {
            final upcoming = list.where((b) => b.departureTime.isAfter(DateTime.now().toUtc())).toList();
            final past = list.where((b) => !b.departureTime.isAfter(DateTime.now().toUtc())).toList();
            if (list.isEmpty) {
              return const _Message(
                icon: Icons.luggage_outlined,
                text: 'No trips yet.\nBook a flight from Search, or add a PNR you booked elsewhere.',
              );
            }
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
              children: [
                for (final b in upcoming) ...[TripCard(booking: b), const SizedBox(height: 14)],
                if (past.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text('Past trips',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(color: ConciergeColors.textSecondary)),
                  ),
                  for (final b in past.reversed) ...[TripCard(booking: b), const SizedBox(height: 14)],
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class TripCard extends ConsumerStatefulWidget {
  const TripCard({super.key, required this.booking});

  final Booking booking;

  @override
  ConsumerState<TripCard> createState() => _TripCardState();
}

class _TripCardState extends ConsumerState<TripCard> {
  bool _triggering = false;

  Future<void> _checkInNow() async {
    setState(() => _triggering = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final message = await ref.read(bookingsProvider.notifier).triggerNow(widget.booking.id);
      messenger.showSnackBar(SnackBar(content: Text(message)));
      // The bot can take a minute; poll a few times for the result.
      for (var i = 0; i < 6 && mounted; i++) {
        await Future<void>.delayed(const Duration(seconds: 10));
        if (!mounted) break;
        await ref.read(bookingsProvider.notifier).refresh();
        final latest = ref
            .read(bookingsProvider)
            .valueOrNull
            ?.where((b) => b.id == widget.booking.id)
            .firstOrNull;
        if (latest == null || latest.status != CheckInStatus.scheduled) break;
      }
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _triggering = false);
    }
  }

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: ConciergeColors.surface,
        title: const Text('Stop tracking this trip?'),
        content: Text('Auto check-in for ${widget.booking.pnrCode} will be cancelled.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Keep')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Remove')),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(bookingsProvider.notifier).delete(widget.booking.id);
    }
  }

  void _openBoardingPass() {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => BoardingPassViewer(
        url: AppConfig.resolveBackendUrl(widget.booking.boardingPassUrl!),
        title: '${widget.booking.flightNumber} · ${widget.booking.pnrCode}',
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final b = widget.booking;
    final theme = Theme.of(context);
    final departs = DateFormat('EEE d MMM yyyy · HH:mm').format(b.departureTime.toLocal());
    final awaiting = b.status == CheckInStatus.pending || b.status == CheckInStatus.scheduled;
    final upcoming = b.departureTime.isAfter(DateTime.now().toUtc());

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(b.flightNumber, style: theme.textTheme.titleLarge),
                      const SizedBox(height: 2),
                      Text(b.passengerName,
                          style: theme.textTheme.bodySmall?.copyWith(color: ConciergeColors.textSecondary)),
                    ],
                  ),
                ),
                StatusChip(status: b.status),
                PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert, color: ConciergeColors.textSecondary),
                  color: ConciergeColors.surfaceHigh,
                  onSelected: (v) {
                    if (v == 'delete') _delete();
                  },
                  itemBuilder: (_) => const [PopupMenuItem(value: 'delete', child: Text('Remove trip'))],
                ),
              ],
            ),
            const SizedBox(height: 14),
            _InfoRow(icon: Icons.confirmation_number_outlined, label: 'PNR', value: b.pnrCode, highlight: true),
            const SizedBox(height: 6),
            _InfoRow(icon: Icons.flight_takeoff, label: 'Departs', value: departs),
            if (b.checkinStrategy != null) ...[
              const SizedBox(height: 6),
              _InfoRow(
                icon: Icons.smart_toy_outlined,
                label: 'Method',
                value: b.checkinStrategy == 'flyo' ? 'Flyo check-in API' : 'Concierge bot',
              ),
            ],
            if (awaiting && upcoming) ...[
              const SizedBox(height: 16),
              CountdownTimer(target: b.checkInOpensAt),
            ],
            if (b.status == CheckInStatus.failed && b.lastError != null) ...[
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: ConciergeColors.danger.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ConciergeColors.danger.withValues(alpha: 0.4)),
                ),
                child: Text(
                  b.lastError!,
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(color: ConciergeColors.danger),
                ),
              ),
            ],
            const SizedBox(height: 16),
            if (b.hasBoardingPass)
              FilledButton.icon(
                onPressed: _openBoardingPass,
                icon: const Icon(Icons.picture_as_pdf_outlined),
                label: const Text('View Boarding Pass'),
              )
            else if (upcoming)
              OutlinedButton.icon(
                onPressed: _triggering ? null : _checkInNow,
                icon: _triggering
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.bolt),
                label: Text(_triggering ? 'Checking in…' : 'Check in now'),
              ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.label, required this.value, this.highlight = false});

  final IconData icon;
  final String label;
  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(icon, size: 16, color: ConciergeColors.gold),
        const SizedBox(width: 8),
        SizedBox(
          width: 64,
          child: Text(label, style: theme.textTheme.labelMedium?.copyWith(color: ConciergeColors.textSecondary)),
        ),
        Expanded(
          child: Text(
            value,
            style: highlight
                ? theme.textTheme.titleSmall?.copyWith(letterSpacing: 2, fontWeight: FontWeight.w700)
                : theme.textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.text, this.action});

  final IconData icon;
  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 80),
        Icon(icon, size: 48, color: ConciergeColors.goldDark),
        const SizedBox(height: 12),
        Text(text,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: ConciergeColors.textSecondary)),
        if (action != null) Center(child: action),
      ],
    );
  }
}

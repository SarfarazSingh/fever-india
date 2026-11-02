import 'dart:async';

import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Live countdown to [target], ticking every second.
class CountdownTimer extends StatefulWidget {
  const CountdownTimer({
    super.key,
    required this.target,
    this.label = 'Check-in opens in',
    this.elapsedLabel = 'Check-in window open',
  });

  final DateTime target;
  final String label;
  final String elapsedLabel;

  @override
  State<CountdownTimer> createState() => _CountdownTimerState();
}

class _CountdownTimerState extends State<CountdownTimer> {
  Timer? _timer;
  late Duration _remaining;

  @override
  void initState() {
    super.initState();
    _remaining = _compute();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
  }

  @override
  void didUpdateWidget(CountdownTimer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.target != widget.target) _remaining = _compute();
  }

  Duration _compute() {
    final remaining = widget.target.difference(DateTime.now().toUtc());
    return remaining.isNegative ? Duration.zero : remaining;
  }

  void _tick() {
    if (!mounted) return;
    setState(() => _remaining = _compute());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (_remaining == Duration.zero) {
      return Row(
        children: [
          const Icon(Icons.bolt, size: 18, color: ConciergeColors.gold),
          const SizedBox(width: 6),
          Text(widget.elapsedLabel,
              style: theme.textTheme.labelLarge?.copyWith(color: ConciergeColors.gold)),
        ],
      );
    }

    final days = _remaining.inDays;
    final hours = _remaining.inHours.remainder(24);
    final minutes = _remaining.inMinutes.remainder(60);
    final seconds = _remaining.inSeconds.remainder(60);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(widget.label,
            style: theme.textTheme.labelMedium?.copyWith(color: ConciergeColors.textSecondary)),
        const SizedBox(height: 6),
        Row(
          children: [
            if (days > 0) ...[_Segment(value: days, unit: 'd'), const SizedBox(width: 6)],
            _Segment(value: hours, unit: 'h'),
            const SizedBox(width: 6),
            _Segment(value: minutes, unit: 'm'),
            const SizedBox(width: 6),
            _Segment(value: seconds, unit: 's'),
          ],
        ),
      ],
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({required this.value, required this.unit});

  final int value;
  final String unit;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: ConciergeColors.surfaceHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: ConciergeColors.outline),
      ),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: value.toString().padLeft(2, '0'),
              style: const TextStyle(
                color: ConciergeColors.textPrimary,
                fontWeight: FontWeight.w700,
                fontSize: 16,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
            TextSpan(
              text: unit,
              style: const TextStyle(color: ConciergeColors.gold, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}

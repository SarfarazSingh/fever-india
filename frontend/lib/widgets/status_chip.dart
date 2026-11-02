import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../data/models/booking.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final CheckInStatus status;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (status) {
      CheckInStatus.pending => (ConciergeColors.textSecondary, Icons.hourglass_empty),
      CheckInStatus.scheduled => (ConciergeColors.gold, Icons.schedule),
      CheckInStatus.completed => (ConciergeColors.success, Icons.verified),
      CheckInStatus.failed => (ConciergeColors.danger, Icons.error_outline),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(status.label,
              style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

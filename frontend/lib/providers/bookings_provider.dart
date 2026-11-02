import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/booking.dart';
import 'api_provider.dart';

class BookingsNotifier extends AsyncNotifier<List<Booking>> {
  @override
  Future<List<Booking>> build() => ref.read(apiClientProvider).listBookings();

  /// Reloads bookings. Keeps the current list visible while refreshing so the
  /// dashboard doesn't flash a spinner on every poll.
  Future<void> refresh() async {
    final next = await AsyncValue.guard(() => ref.read(apiClientProvider).listBookings());
    if (next.hasError && state.hasValue) return;
    state = next;
  }

  Future<Booking> register(BookingRequest request) async {
    final booking = await ref.read(apiClientProvider).registerCheckIn(request);
    final current = state.valueOrNull ?? const <Booking>[];
    final merged = [
      ...current.where((b) => b.id != booking.id),
      booking,
    ]..sort((a, b) => a.departureTime.compareTo(b.departureTime));
    state = AsyncValue.data(merged);
    return booking;
  }

  Future<String> triggerNow(int bookingId) async {
    final message = await ref.read(apiClientProvider).triggerCheckInNow(bookingId);
    await refresh();
    return message;
  }

  Future<void> delete(int bookingId) async {
    await ref.read(apiClientProvider).deleteBooking(bookingId);
    final current = state.valueOrNull ?? const <Booking>[];
    state = AsyncValue.data(current.where((b) => b.id != bookingId).toList());
  }
}

final bookingsProvider = AsyncNotifierProvider<BookingsNotifier, List<Booking>>(BookingsNotifier.new);

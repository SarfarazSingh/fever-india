import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/config.dart';
import 'models/booking.dart';
import 'models/flight_offer.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class FlightSearchResult {
  final String provider;
  final List<FlightOffer> offers;

  const FlightSearchResult({required this.provider, required this.offers});
}

class ApiClient {
  ApiClient({Dio? dio, String? baseUrl})
      : _dio = dio ??
            Dio(BaseOptions(
              baseUrl: baseUrl ?? AppConfig.apiBaseUrl,
              connectTimeout: const Duration(seconds: 8),
              receiveTimeout: const Duration(seconds: 30),
              headers: {'Accept': 'application/json'},
            ));

  final Dio _dio;

  Future<FlightSearchResult> searchFlights({
    required String origin,
    required String destination,
    required DateTime date,
  }) async {
    final data = await _get('/api/flights/search', query: {
      'origin': origin.toUpperCase(),
      'destination': destination.toUpperCase(),
      'date': DateFormat('yyyy-MM-dd').format(date),
    });
    final results = (data['results'] as List<dynamic>)
        .map((e) => FlightOffer.fromJson(e as Map<String, dynamic>))
        .toList();
    return FlightSearchResult(provider: data['provider'] as String? ?? 'unknown', offers: results);
  }

  Future<List<Booking>> listBookings({String? email}) async {
    final data = await _get('/api/bookings', query: {if (email != null) 'email': email});
    return (data as List<dynamic>).map((e) => Booking.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Booking> registerCheckIn(BookingRequest request) async {
    final data = await _send(() => _dio.post('/api/bookings/register-checkin', data: request.toJson()));
    return Booking.fromJson(data as Map<String, dynamic>);
  }

  Future<String> triggerCheckInNow(int bookingId) async {
    final data = await _send(() => _dio.post('/api/bookings/$bookingId/trigger-checkin-now'));
    return (data as Map<String, dynamic>)['message'] as String? ?? 'Check-in started';
  }

  Future<void> deleteBooking(int bookingId) async {
    await _send(() => _dio.delete('/api/bookings/$bookingId'));
  }

  Future<dynamic> _get(String path, {Map<String, dynamic>? query}) =>
      _send(() => _dio.get(path, queryParameters: query));

  Future<dynamic> _send(Future<Response<dynamic>> Function() call) async {
    try {
      final response = await call();
      return response.data;
    } on DioException catch (e) {
      throw ApiException(_describe(e), statusCode: e.response?.statusCode);
    }
  }

  String _describe(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      final d = detail['detail'];
      if (d is String) return d;
      if (d is List && d.isNotEmpty && d.first is Map) {
        final first = d.first as Map;
        final loc = (first['loc'] as List?)?.where((p) => p != 'body').join('.') ?? '';
        return '${loc.isEmpty ? '' : '$loc: '}${first['msg']}';
      }
    }
    return switch (e.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.connectionError =>
        'Cannot reach the concierge server at ${AppConfig.apiBaseUrl}.',
      DioExceptionType.receiveTimeout => 'The server took too long to respond.',
      _ => 'Request failed (${e.response?.statusCode ?? e.type.name}).',
    };
  }
}

import 'package:business_concierge/core/config.dart';
import 'package:business_concierge/data/models/booking.dart';
import 'package:business_concierge/data/models/flight_offer.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FlightOffer parses backend JSON and keeps airport wall-clock times', () {
    final offer = FlightOffer.fromJson({
      'id': 'mock-QR-JFKDOH-20261215-0',
      'airline_name': 'Qatar Airways',
      'airline_iata': 'QR',
      'flight_number': 'QR719',
      'origin': 'JFK',
      'destination': 'DOH',
      'departure_time': '2026-12-16T03:10:00Z',
      'arrival_time': '2026-12-16T15:40:00Z',
      'departure_local': '2026-12-15T22:10:00',
      'arrival_local': '2026-12-16T18:40:00',
      'duration_minutes': 750,
      'layovers': 0,
      'layover_airports': <String>[],
      'price': 4230.13,
      'currency': 'USD',
      'cabin_class': 'C',
      'deep_link': 'http://localhost:8000/demo/checkout?carrier=QR',
      'segments': <Map<String, dynamic>>[],
      'provider': 'mock',
    });
    expect(offer.departureLocal.hour, 22);
    expect(offer.departureTime.isUtc, isTrue);
    expect(offer.arrivalDayOffset, 1);
    expect(offer.durationLabel, '12h 30m');
    expect(offer.stopsLabel, 'Nonstop');
  });

  test('BookingRequest normalises fields for the API', () {
    final json = BookingRequest(
      userEmail: ' ada@example.com ',
      passengerFirstName: 'Ada',
      passengerLastName: 'Lovelace',
      airlineIata: 'dl',
      flightNumber: 'dl 1',
      departureTime: DateTime.utc(2026, 12, 1, 10),
      pnrCode: 'abc123',
    ).toJson();
    expect(json['airline_iata'], 'DL');
    expect(json['flight_number'], 'DL1');
    expect(json['pnr_code'], 'ABC123');
    expect(json['departure_time'], '2026-12-01T10:00:00.000Z');
  });

  test('CheckInStatus parses backend values', () {
    expect(CheckInStatus.parse('SCHEDULED'), CheckInStatus.scheduled);
    expect(CheckInStatus.parse('COMPLETED'), CheckInStatus.completed);
    expect(CheckInStatus.parse('FAILED'), CheckInStatus.failed);
  });

  test('resolveBackendUrl rewrites localhost links to the API host', () {
    final resolved = AppConfig.resolveBackendUrl('http://localhost:8000/static/boarding_passes/A.pdf');
    expect(resolved, startsWith(AppConfig.apiBaseUrl));
    expect(AppConfig.resolveBackendUrl('https://www.delta.com/x'), 'https://www.delta.com/x');
  });
}

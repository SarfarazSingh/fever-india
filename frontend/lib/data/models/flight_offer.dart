class FlightSegment {
  final String airlineIata;
  final String airlineName;
  final String flightNumber;
  final String origin;
  final String destination;
  final DateTime departureTime; // UTC
  final DateTime arrivalTime; // UTC
  final DateTime departureLocal; // airport wall-clock
  final DateTime arrivalLocal;

  const FlightSegment({
    required this.airlineIata,
    required this.airlineName,
    required this.flightNumber,
    required this.origin,
    required this.destination,
    required this.departureTime,
    required this.arrivalTime,
    required this.departureLocal,
    required this.arrivalLocal,
  });

  factory FlightSegment.fromJson(Map<String, dynamic> json) => FlightSegment(
        airlineIata: json['airline_iata'] as String,
        airlineName: json['airline_name'] as String,
        flightNumber: json['flight_number'] as String,
        origin: json['origin'] as String,
        destination: json['destination'] as String,
        departureTime: DateTime.parse(json['departure_time'] as String).toUtc(),
        arrivalTime: DateTime.parse(json['arrival_time'] as String).toUtc(),
        departureLocal: parseWallClock(json['departure_local'] as String),
        arrivalLocal: parseWallClock(json['arrival_local'] as String),
      );
}

class FlightOffer {
  final String id;
  final String airlineName;
  final String airlineIata;
  final String flightNumber;
  final String origin;
  final String destination;
  final DateTime departureTime;
  final DateTime arrivalTime;
  final DateTime departureLocal;
  final DateTime arrivalLocal;
  final int durationMinutes;
  final int layovers;
  final List<String> layoverAirports;
  final double price;
  final String currency;
  final String cabinClass;
  final String deepLink;
  final List<FlightSegment> segments;
  final String provider;

  const FlightOffer({
    required this.id,
    required this.airlineName,
    required this.airlineIata,
    required this.flightNumber,
    required this.origin,
    required this.destination,
    required this.departureTime,
    required this.arrivalTime,
    required this.departureLocal,
    required this.arrivalLocal,
    required this.durationMinutes,
    required this.layovers,
    required this.layoverAirports,
    required this.price,
    required this.currency,
    required this.cabinClass,
    required this.deepLink,
    required this.segments,
    required this.provider,
  });

  factory FlightOffer.fromJson(Map<String, dynamic> json) => FlightOffer(
        id: json['id'] as String,
        airlineName: json['airline_name'] as String,
        airlineIata: json['airline_iata'] as String,
        flightNumber: json['flight_number'] as String,
        origin: json['origin'] as String,
        destination: json['destination'] as String,
        departureTime: DateTime.parse(json['departure_time'] as String).toUtc(),
        arrivalTime: DateTime.parse(json['arrival_time'] as String).toUtc(),
        departureLocal: parseWallClock(json['departure_local'] as String),
        arrivalLocal: parseWallClock(json['arrival_local'] as String),
        durationMinutes: (json['duration_minutes'] as num).toInt(),
        layovers: (json['layovers'] as num).toInt(),
        layoverAirports: (json['layover_airports'] as List<dynamic>? ?? const []).cast<String>(),
        price: (json['price'] as num).toDouble(),
        currency: json['currency'] as String,
        cabinClass: json['cabin_class'] as String? ?? 'C',
        deepLink: json['deep_link'] as String,
        segments: (json['segments'] as List<dynamic>)
            .map((s) => FlightSegment.fromJson(s as Map<String, dynamic>))
            .toList(),
        provider: json['provider'] as String? ?? 'unknown',
      );

  String get durationLabel {
    final h = durationMinutes ~/ 60;
    final m = durationMinutes % 60;
    return m == 0 ? '${h}h' : '${h}h ${m}m';
  }

  String get stopsLabel {
    if (layovers == 0) return 'Nonstop';
    final via = layoverAirports.join(', ');
    return '$layovers stop${layovers > 1 ? 's' : ''}${via.isEmpty ? '' : ' via $via'}';
  }

  /// Whole days between local departure and arrival dates (e.g. "+1").
  int get arrivalDayOffset {
    final d = DateTime(departureLocal.year, departureLocal.month, departureLocal.day);
    final a = DateTime(arrivalLocal.year, arrivalLocal.month, arrivalLocal.day);
    return a.difference(d).inDays;
  }
}

/// Parses an ISO timestamp without offset as a wall-clock time, so it is
/// displayed exactly as the airport's local time regardless of device zone.
DateTime parseWallClock(String value) {
  final stripped = value.replaceFirst(RegExp(r'(Z|[+-]\d{2}:?\d{2})$'), '');
  return DateTime.parse(stripped);
}

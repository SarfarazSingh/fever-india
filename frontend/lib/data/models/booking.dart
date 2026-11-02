enum CheckInStatus {
  pending,
  scheduled,
  completed,
  failed;

  static CheckInStatus parse(String value) => switch (value.toUpperCase()) {
        'SCHEDULED' => CheckInStatus.scheduled,
        'COMPLETED' => CheckInStatus.completed,
        'FAILED' => CheckInStatus.failed,
        _ => CheckInStatus.pending,
      };

  String get label => switch (this) {
        CheckInStatus.pending => 'Pending',
        CheckInStatus.scheduled => 'Scheduled',
        CheckInStatus.completed => 'Checked in',
        CheckInStatus.failed => 'Needs attention',
      };
}

class Booking {
  final int id;
  final String userEmail;
  final String passengerFirstName;
  final String passengerLastName;
  final String airlineIata;
  final String flightNumber;
  final DateTime departureTime; // UTC
  final String pnrCode;
  final CheckInStatus status;
  final String? boardingPassUrl;
  final DateTime? checkinScheduledFor;
  final String? checkinStrategy;
  final String? lastError;

  const Booking({
    required this.id,
    required this.userEmail,
    required this.passengerFirstName,
    required this.passengerLastName,
    required this.airlineIata,
    required this.flightNumber,
    required this.departureTime,
    required this.pnrCode,
    required this.status,
    this.boardingPassUrl,
    this.checkinScheduledFor,
    this.checkinStrategy,
    this.lastError,
  });

  factory Booking.fromJson(Map<String, dynamic> json) => Booking(
        id: (json['id'] as num).toInt(),
        userEmail: json['user_email'] as String,
        passengerFirstName: json['passenger_first_name'] as String,
        passengerLastName: json['passenger_last_name'] as String,
        airlineIata: json['airline_iata'] as String,
        flightNumber: json['flight_number'] as String,
        departureTime: DateTime.parse(json['departure_time'] as String).toUtc(),
        pnrCode: json['pnr_code'] as String,
        status: CheckInStatus.parse(json['check_in_status'] as String),
        boardingPassUrl: json['boarding_pass_url'] as String?,
        checkinScheduledFor: json['checkin_scheduled_for'] == null
            ? null
            : DateTime.parse(json['checkin_scheduled_for'] as String).toUtc(),
        checkinStrategy: json['checkin_strategy'] as String?,
        lastError: json['last_error'] as String?,
      );

  String get passengerName => '$passengerFirstName $passengerLastName';

  DateTime get checkInOpensAt =>
      checkinScheduledFor ?? departureTime.subtract(const Duration(hours: 24));

  bool get hasBoardingPass => boardingPassUrl != null && boardingPassUrl!.isNotEmpty;
}

class BookingRequest {
  final String userEmail;
  final String passengerFirstName;
  final String passengerLastName;
  final String airlineIata;
  final String flightNumber;
  final DateTime departureTime;
  final String pnrCode;

  const BookingRequest({
    required this.userEmail,
    required this.passengerFirstName,
    required this.passengerLastName,
    required this.airlineIata,
    required this.flightNumber,
    required this.departureTime,
    required this.pnrCode,
  });

  Map<String, dynamic> toJson() => {
        'user_email': userEmail.trim(),
        'passenger_first_name': passengerFirstName.trim(),
        'passenger_last_name': passengerLastName.trim(),
        'airline_iata': airlineIata.trim().toUpperCase(),
        'flight_number': flightNumber.trim().toUpperCase().replaceAll(' ', ''),
        'departure_time': departureTime.toUtc().toIso8601String(),
        'pnr_code': pnrCode.trim().toUpperCase(),
      };
}

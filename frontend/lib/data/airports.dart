class Airport {
  final String iata;
  final String city;
  final String name;

  const Airport(this.iata, this.city, this.name);

  String get label => '$city ($iata)';

  bool matches(String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return false;
    return iata.toLowerCase().startsWith(q) ||
        city.toLowerCase().contains(q) ||
        name.toLowerCase().contains(q);
  }
}

const airports = <Airport>[
  Airport('ATL', 'Atlanta', 'Hartsfield-Jackson'),
  Airport('BOS', 'Boston', 'Logan International'),
  Airport('DFW', 'Dallas', 'Dallas/Fort Worth International'),
  Airport('DEN', 'Denver', 'Denver International'),
  Airport('EWR', 'Newark', 'Newark Liberty International'),
  Airport('IAD', 'Washington', 'Dulles International'),
  Airport('IAH', 'Houston', 'George Bush Intercontinental'),
  Airport('JFK', 'New York', 'John F. Kennedy International'),
  Airport('LAX', 'Los Angeles', 'Los Angeles International'),
  Airport('MIA', 'Miami', 'Miami International'),
  Airport('ORD', 'Chicago', "O'Hare International"),
  Airport('SEA', 'Seattle', 'Seattle-Tacoma International'),
  Airport('SFO', 'San Francisco', 'San Francisco International'),
  Airport('YYZ', 'Toronto', 'Pearson International'),
  Airport('YVR', 'Vancouver', 'Vancouver International'),
  Airport('MEX', 'Mexico City', 'Benito Juarez International'),
  Airport('GRU', 'Sao Paulo', 'Guarulhos International'),
  Airport('EZE', 'Buenos Aires', 'Ministro Pistarini'),
  Airport('LHR', 'London', 'Heathrow'),
  Airport('LGW', 'London', 'Gatwick'),
  Airport('CDG', 'Paris', 'Charles de Gaulle'),
  Airport('AMS', 'Amsterdam', 'Schiphol'),
  Airport('FRA', 'Frankfurt', 'Frankfurt am Main'),
  Airport('MUC', 'Munich', 'Franz Josef Strauss'),
  Airport('ZRH', 'Zurich', 'Zurich Airport'),
  Airport('GVA', 'Geneva', 'Geneva Airport'),
  Airport('VIE', 'Vienna', 'Vienna International'),
  Airport('MAD', 'Madrid', 'Adolfo Suarez Madrid-Barajas'),
  Airport('BCN', 'Barcelona', 'El Prat'),
  Airport('FCO', 'Rome', 'Fiumicino'),
  Airport('MXP', 'Milan', 'Malpensa'),
  Airport('LIS', 'Lisbon', 'Humberto Delgado'),
  Airport('DUB', 'Dublin', 'Dublin Airport'),
  Airport('CPH', 'Copenhagen', 'Kastrup'),
  Airport('IST', 'Istanbul', 'Istanbul Airport'),
  Airport('DOH', 'Doha', 'Hamad International'),
  Airport('DXB', 'Dubai', 'Dubai International'),
  Airport('AUH', 'Abu Dhabi', 'Zayed International'),
  Airport('RUH', 'Riyadh', 'King Khalid International'),
  Airport('DEL', 'Delhi', 'Indira Gandhi International'),
  Airport('BOM', 'Mumbai', 'Chhatrapati Shivaji Maharaj'),
  Airport('BLR', 'Bengaluru', 'Kempegowda International'),
  Airport('SIN', 'Singapore', 'Changi'),
  Airport('HKG', 'Hong Kong', 'Hong Kong International'),
  Airport('BKK', 'Bangkok', 'Suvarnabhumi'),
  Airport('KUL', 'Kuala Lumpur', 'KLIA'),
  Airport('NRT', 'Tokyo', 'Narita'),
  Airport('HND', 'Tokyo', 'Haneda'),
  Airport('ICN', 'Seoul', 'Incheon International'),
  Airport('PEK', 'Beijing', 'Capital International'),
  Airport('PVG', 'Shanghai', 'Pudong International'),
  Airport('TPE', 'Taipei', 'Taoyuan International'),
  Airport('SYD', 'Sydney', 'Kingsford Smith'),
  Airport('MEL', 'Melbourne', 'Tullamarine'),
  Airport('AKL', 'Auckland', 'Auckland Airport'),
  Airport('JNB', 'Johannesburg', 'O. R. Tambo International'),
  Airport('CPT', 'Cape Town', 'Cape Town International'),
  Airport('CAI', 'Cairo', 'Cairo International'),
  Airport('NBO', 'Nairobi', 'Jomo Kenyatta International'),
  Airport('ADD', 'Addis Ababa', 'Bole International'),
];

Airport? airportByIata(String code) {
  final c = code.trim().toUpperCase();
  for (final a in airports) {
    if (a.iata == c) return a;
  }
  return null;
}

List<Airport> searchAirports(String query, {int limit = 8}) =>
    airports.where((a) => a.matches(query)).take(limit).toList();

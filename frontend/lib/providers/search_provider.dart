import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api_client.dart';
import '../data/models/flight_offer.dart';
import 'api_provider.dart';

class SearchState {
  final String origin;
  final String destination;
  final DateTime date;
  final AsyncValue<List<FlightOffer>>? results;
  final String? provider;

  const SearchState({
    required this.origin,
    required this.destination,
    required this.date,
    this.results,
    this.provider,
  });

  bool get canSearch =>
      origin.length == 3 && destination.length == 3 && origin != destination;

  SearchState copyWith({
    String? origin,
    String? destination,
    DateTime? date,
    AsyncValue<List<FlightOffer>>? results,
    String? provider,
  }) =>
      SearchState(
        origin: origin ?? this.origin,
        destination: destination ?? this.destination,
        date: date ?? this.date,
        results: results ?? this.results,
        provider: provider ?? this.provider,
      );
}

class SearchNotifier extends StateNotifier<SearchState> {
  SearchNotifier(this._api)
      : super(SearchState(
          origin: 'JFK',
          destination: 'LHR',
          date: DateTime.now().add(const Duration(days: 21)),
        ));

  final ApiClient _api;
  int _requestId = 0;

  void setOrigin(String iata) => state = state.copyWith(origin: iata.toUpperCase());

  void setDestination(String iata) => state = state.copyWith(destination: iata.toUpperCase());

  void setDate(DateTime date) => state = state.copyWith(date: date);

  void swap() => state = state.copyWith(origin: state.destination, destination: state.origin);

  Future<void> search() async {
    if (!state.canSearch) {
      state = state.copyWith(
        results: AsyncValue.error(
          const ApiException('Choose two different 3-letter airport codes.'),
          StackTrace.current,
        ),
      );
      return;
    }
    final id = ++_requestId;
    state = state.copyWith(results: const AsyncValue.loading());
    try {
      final result = await _api.searchFlights(
        origin: state.origin,
        destination: state.destination,
        date: state.date,
      );
      if (id != _requestId) return;
      state = state.copyWith(results: AsyncValue.data(result.offers), provider: result.provider);
    } catch (e, st) {
      if (id != _requestId) return;
      state = state.copyWith(results: AsyncValue.error(e, st));
    }
  }
}

final searchProvider = StateNotifierProvider<SearchNotifier, SearchState>(
  (ref) => SearchNotifier(ref.watch(apiClientProvider)),
);

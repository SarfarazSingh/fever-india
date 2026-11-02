import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api_client.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Traveller details remembered for the session to prefill check-in forms.
class TravellerProfile {
  final String email;
  final String firstName;
  final String lastName;

  const TravellerProfile({this.email = '', this.firstName = '', this.lastName = ''});
}

final travellerProfileProvider = StateProvider<TravellerProfile>((ref) => const TravellerProfile());

import 'package:flutter/foundation.dart';

class AppConfig {
  static const _fromEnv = String.fromEnvironment('API_BASE_URL');

  /// Base URL of the FastAPI backend.
  ///
  /// Override with `--dart-define=API_BASE_URL=https://api.example.com`.
  /// The Android emulator reaches the host machine via 10.0.2.2.
  static String get apiBaseUrl {
    if (_fromEnv.isNotEmpty) return _stripSlash(_fromEnv);
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://localhost:8000';
  }

  /// Rewrites backend-generated links that point at localhost (demo checkout
  /// pages, locally stored boarding passes) so they resolve from the device.
  static String resolveBackendUrl(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return url;
    if (!uri.hasScheme) {
      return '$apiBaseUrl${url.startsWith('/') ? '' : '/'}$url';
    }
    const localHosts = {'localhost', '127.0.0.1', '0.0.0.0'};
    if (!localHosts.contains(uri.host)) return url;
    final api = Uri.parse(apiBaseUrl);
    return uri.replace(scheme: api.scheme, host: api.host, port: api.port).toString();
  }

  static String _stripSlash(String v) => v.endsWith('/') ? v.substring(0, v.length - 1) : v;
}

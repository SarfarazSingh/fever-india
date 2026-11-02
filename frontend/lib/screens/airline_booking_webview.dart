import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app.dart';
import '../core/config.dart';
import '../core/theme.dart';
import '../data/models/flight_offer.dart';
import '../widgets/pnr_confirmation_sheet.dart';

/// Scans the page text for airline confirmation codes and reports each new
/// one to Flutter. Idempotent: re-injecting on the same document only rescans.
/// A MutationObserver (plus a slow periodic rescan) catches codes rendered or
/// revealed after load, as on single-page checkouts.
const String pnrScannerJs = r'''
(function () {
  if (window.__conciergePnrWatcher) { window.__conciergePnrWatcher.scan(); return; }

  var pattern = /(?:PNR|Confirmation|Record\s+Locator|Booking\s+Reference)(?:\s*(?:number|code|no\.?|#))?(?:\s+is)?[:\s#]+([A-Z0-9]{6})\b/gi;
  var ignore = { NUMBER: 1, PLEASE: 1, STATUS: 1, DETAIL: 1, CHANGE: 1, CANCEL: 1, REVIEW: 1,
                 BOOKED: 1, EMAILS: 1, SHOULD: 1, WITHIN: 1, RECORD: 1, LOCATE: 1, NOTICE: 1 };
  var reported = {};

  function report(code) {
    if (reported[code]) return;
    reported[code] = true;
    if (window.flutter_inappwebview && window.flutter_inappwebview.callHandler) {
      window.flutter_inappwebview.callHandler('pnrDetected', code, location.href);
    }
  }

  function scan() {
    var text = document.body ? document.body.innerText : '';
    pattern.lastIndex = 0;
    var m;
    while ((m = pattern.exec(text)) !== null) {
      var code = m[1].toUpperCase();
      if (!ignore[code]) report(code);
    }
  }

  var timer = null;
  var observer = new MutationObserver(function () {
    clearTimeout(timer);
    timer = setTimeout(scan, 400);
  });
  // Attribute changes matter: confirmations are often revealed by toggling
  // style/class on an element that already holds the code.
  observer.observe(document.documentElement, {
    childList: true, subtree: true, characterData: true,
    attributes: true, attributeFilter: ['style', 'class', 'hidden', 'aria-hidden']
  });
  setInterval(scan, 3000);

  window.__conciergePnrWatcher = { scan: scan };
  scan();
})();
''';

class AirlineBookingWebView extends ConsumerStatefulWidget {
  const AirlineBookingWebView({super.key, required this.offer});

  final FlightOffer offer;

  @override
  ConsumerState<AirlineBookingWebView> createState() => _AirlineBookingWebViewState();
}

class _AirlineBookingWebViewState extends ConsumerState<AirlineBookingWebView> {
  InAppWebViewController? _controller;
  final Set<String> _handledCodes = {};
  double _progress = 0;
  String _host = '';
  bool _sheetOpen = false;

  late final String _initialUrl = AppConfig.resolveBackendUrl(widget.offer.deepLink);

  @override
  void initState() {
    super.initState();
    _host = Uri.tryParse(_initialUrl)?.host ?? '';
  }

  Future<void> _onPnrDetected(String code) async {
    final pnr = code.toUpperCase();
    if (_handledCodes.contains(pnr) || _sheetOpen || !mounted) return;
    _handledCodes.add(pnr);
    await _showSheet(pnr);
  }

  Future<void> _showSheet(String pnr) async {
    _sheetOpen = true;
    final booking = await showPnrConfirmationSheet(context, pnr: pnr, offer: widget.offer);
    _sheetOpen = false;
    if (booking == null || !mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Auto check-in scheduled for ${booking.pnrCode}.'),
        action: SnackBarAction(
          label: 'My Trips',
          textColor: ConciergeColors.gold,
          onPressed: () {
            ref.read(homeTabProvider.notifier).state = 1;
            Navigator.of(context).popUntil((r) => r.isFirst);
          },
        ),
      ),
    );
  }

  Future<NavigationActionPolicy> _shouldOverride(
    InAppWebViewController controller,
    NavigationAction action,
  ) async {
    final uri = action.request.url;
    if (uri == null) return NavigationActionPolicy.ALLOW;
    const webSchemes = {'http', 'https', 'about', 'data', 'blob', 'javascript'};
    if (webSchemes.contains(uri.scheme)) return NavigationActionPolicy.ALLOW;
    // mailto:, tel:, intent:, airline app links, wallet passes...
    await launchUrl(uri, mode: LaunchMode.externalApplication);
    return NavigationActionPolicy.CANCEL;
  }

  @override
  Widget build(BuildContext context) {
    final offer = widget.offer;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${offer.airlineName} · ${offer.flightNumber}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(color: ConciergeColors.gold)),
            Row(
              children: [
                const Icon(Icons.lock, size: 12, color: ConciergeColors.textSecondary),
                const SizedBox(width: 4),
                Flexible(
                  child: Text(_host,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: ConciergeColors.textSecondary)),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'I have a booking code',
            icon: const Icon(Icons.confirmation_number_outlined),
            onPressed: () => _showSheet(''),
          ),
          IconButton(
            tooltip: 'Reload',
            icon: const Icon(Icons.refresh),
            onPressed: () => _controller?.reload(),
          ),
          IconButton(
            tooltip: 'Open in browser',
            icon: const Icon(Icons.open_in_browser),
            onPressed: () async {
              final current = await _controller?.getUrl();
              await launchUrl(current ?? Uri.parse(_initialUrl), mode: LaunchMode.externalApplication);
            },
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(2),
          child: _progress < 1
              ? LinearProgressIndicator(value: _progress, minHeight: 2, backgroundColor: Colors.transparent)
              : const SizedBox(height: 2),
        ),
      ),
      body: InAppWebView(
        initialUrlRequest: URLRequest(url: WebUri(_initialUrl)),
        initialSettings: InAppWebViewSettings(
          javaScriptEnabled: true,
          domStorageEnabled: true,
          useShouldOverrideUrlLoading: true,
          mediaPlaybackRequiresUserGesture: true,
          allowsInlineMediaPlayback: true,
          supportMultipleWindows: false,
          thirdPartyCookiesEnabled: true,
          transparentBackground: false,
        ),
        onWebViewCreated: (controller) {
          _controller = controller;
          controller.addJavaScriptHandler(
            handlerName: 'pnrDetected',
            callback: (args) {
              if (args.isNotEmpty && args.first is String) {
                _onPnrDetected(args.first as String);
              }
              return true;
            },
          );
        },
        shouldOverrideUrlLoading: _shouldOverride,
        onProgressChanged: (_, progress) => setState(() => _progress = progress / 100),
        onLoadStart: (_, url) => setState(() => _host = url?.host ?? _host),
        onLoadStop: (controller, url) async {
          setState(() => _progress = 1);
          await controller.evaluateJavascript(source: pnrScannerJs);
        },
        onReceivedError: (controller, request, error) {
          if (request.isForMainFrame != true || !mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not load page: ${error.description}')),
          );
        },
      ),
    );
  }
}

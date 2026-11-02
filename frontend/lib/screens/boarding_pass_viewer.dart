import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/theme.dart';

/// Shows a boarding pass PDF or image in-app.
///
/// Android's WebView cannot render PDFs, so on Android PDFs are handed to the
/// system viewer instead; images render in-app on every platform.
class BoardingPassViewer extends StatefulWidget {
  const BoardingPassViewer({super.key, required this.url, required this.title});

  final String url;
  final String title;

  @override
  State<BoardingPassViewer> createState() => _BoardingPassViewerState();
}

class _BoardingPassViewerState extends State<BoardingPassViewer> {
  double _progress = 0;

  bool get _isPdf => Uri.tryParse(widget.url)?.path.toLowerCase().endsWith('.pdf') ?? false;

  bool get _renderInApp => !_isPdf || kIsWeb || defaultTargetPlatform != TargetPlatform.android;

  Future<void> _openExternally() async {
    final ok = await launchUrl(Uri.parse(widget.url), mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No app available to open the boarding pass.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        actions: [
          IconButton(
            tooltip: 'Open externally',
            icon: const Icon(Icons.ios_share),
            onPressed: _openExternally,
          ),
        ],
        bottom: _renderInApp && _progress < 1
            ? PreferredSize(
                preferredSize: const Size.fromHeight(2),
                child: LinearProgressIndicator(value: _progress, minHeight: 2),
              )
            : null,
      ),
      body: _renderInApp
          ? InAppWebView(
              initialUrlRequest: URLRequest(url: WebUri(widget.url)),
              initialSettings: InAppWebViewSettings(
                javaScriptEnabled: false,
                supportZoom: true,
                builtInZoomControls: true,
                displayZoomControls: false,
                transparentBackground: true,
              ),
              onProgressChanged: (_, p) => setState(() => _progress = p / 100),
            )
          : Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 72,
                      height: 72,
                      decoration: const BoxDecoration(shape: BoxShape.circle, gradient: ConciergeColors.goldGradient),
                      child: const Icon(Icons.airplane_ticket, size: 36, color: Colors.black),
                    ),
                    const SizedBox(height: 20),
                    Text('Your boarding pass is ready', style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 8),
                    Text(
                      'Open the PDF in your device viewer to save it or add it to your wallet.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: ConciergeColors.textSecondary),
                    ),
                    const SizedBox(height: 24),
                    FilledButton.icon(
                      onPressed: _openExternally,
                      icon: const Icon(Icons.picture_as_pdf),
                      label: const Text('Open Boarding Pass PDF'),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}

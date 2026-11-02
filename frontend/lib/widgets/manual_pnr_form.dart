import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/theme.dart';
import '../data/models/booking.dart';
import '../data/models/flight_offer.dart';
import '../providers/api_provider.dart';
import '../providers/bookings_provider.dart';

/// Opens the "add a booking booked elsewhere" sheet. Resolves to the
/// registered booking, or null if dismissed.
Future<Booking?> showManualPnrForm(BuildContext context) {
  return showModalBottomSheet<Booking>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => BookingDetailsForm(
      header: Builder(
        builder: (context) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Add a trip', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 6),
            Text(
              'Booked elsewhere? Enter your record locator and we will check you in '
              '24 hours before departure.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: ConciergeColors.textSecondary),
            ),
          ],
        ),
      ),
      submitLabel: 'Schedule auto check-in',
    ),
  );
}

class BookingDetailsForm extends ConsumerStatefulWidget {
  const BookingDetailsForm({
    super.key,
    this.header,
    this.initialPnr,
    this.offer,
    this.submitLabel = 'Save',
    this.cancelLabel = 'Cancel',
  });

  final Widget? header;
  final String? initialPnr;

  /// When provided, airline, flight number and departure are taken from the
  /// offer and shown read-only.
  final FlightOffer? offer;
  final String submitLabel;
  final String cancelLabel;

  @override
  ConsumerState<BookingDetailsForm> createState() => _BookingDetailsFormState();
}

class _BookingDetailsFormState extends ConsumerState<BookingDetailsForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _pnr;
  late final TextEditingController _airline;
  late final TextEditingController _flight;
  late final TextEditingController _first;
  late final TextEditingController _last;
  late final TextEditingController _email;
  DateTime? _departureLocal; // device-local, used when no offer is supplied
  bool _submitting = false;
  String? _error;

  static final _alnum = RegExp(r'^[A-Za-z0-9]+$');

  @override
  void initState() {
    super.initState();
    final profile = ref.read(travellerProfileProvider);
    final offer = widget.offer;
    _pnr = TextEditingController(text: widget.initialPnr ?? '');
    _airline = TextEditingController(text: offer?.airlineIata ?? '');
    _flight = TextEditingController(text: offer?.flightNumber ?? '');
    _first = TextEditingController(text: profile.firstName);
    _last = TextEditingController(text: profile.lastName);
    _email = TextEditingController(text: profile.email);
  }

  @override
  void dispose() {
    for (final c in [_pnr, _airline, _flight, _first, _last, _email]) {
      c.dispose();
    }
    super.dispose();
  }

  DateTime? get _departureUtc => widget.offer?.departureTime ?? _departureLocal?.toUtc();

  Future<void> _pickDeparture() async {
    final now = DateTime.now();
    final initial = _departureLocal ?? now.add(const Duration(days: 2));
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(initial));
    if (time == null || !mounted) return;
    setState(() {
      _departureLocal = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    });
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    if (!_formKey.currentState!.validate()) return;
    final departure = _departureUtc;
    if (departure == null) {
      setState(() => _error = 'Choose the departure date and time.');
      return;
    }
    if (departure.isBefore(DateTime.now().toUtc())) {
      setState(() => _error = 'Departure must be in the future.');
      return;
    }

    setState(() => _submitting = true);
    try {
      final booking = await ref.read(bookingsProvider.notifier).register(BookingRequest(
            userEmail: _email.text,
            passengerFirstName: _first.text,
            passengerLastName: _last.text,
            airlineIata: _airline.text,
            flightNumber: _flight.text,
            departureTime: departure,
            pnrCode: _pnr.text,
          ));
      ref.read(travellerProfileProvider.notifier).state = TravellerProfile(
        email: _email.text.trim(),
        firstName: _first.text.trim(),
        lastName: _last.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(booking);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final offer = widget.offer;
    final insets = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + insets),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.header != null) ...[widget.header!, const SizedBox(height: 20)],
              TextFormField(
                controller: _pnr,
                textCapitalization: TextCapitalization.characters,
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp('[A-Za-z0-9]')),
                  LengthLimitingTextInputFormatter(6),
                  _UpperCaseFormatter(),
                ],
                decoration: const InputDecoration(
                  labelText: 'Booking code (PNR)',
                  prefixIcon: Icon(Icons.confirmation_number_outlined),
                ),
                validator: (v) =>
                    (v == null || v.length != 6 || !_alnum.hasMatch(v)) ? 'Enter the 6-character code' : null,
              ),
              const SizedBox(height: 12),
              if (offer != null)
                _FlightSummary(offer: offer)
              else ...[
                Row(
                  children: [
                    Expanded(
                      flex: 2,
                      child: TextFormField(
                        controller: _airline,
                        textCapitalization: TextCapitalization.characters,
                        inputFormatters: [LengthLimitingTextInputFormatter(2), _UpperCaseFormatter()],
                        decoration: const InputDecoration(labelText: 'Airline', hintText: 'DL'),
                        validator: (v) =>
                            (v == null || v.length != 2 || !_alnum.hasMatch(v)) ? '2-letter code' : null,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 3,
                      child: TextFormField(
                        controller: _flight,
                        textCapitalization: TextCapitalization.characters,
                        inputFormatters: [LengthLimitingTextInputFormatter(8), _UpperCaseFormatter()],
                        decoration: const InputDecoration(labelText: 'Flight no.', hintText: 'DL1'),
                        validator: (v) {
                          final s = (v ?? '').replaceAll(' ', '');
                          return (s.isEmpty || !_alnum.hasMatch(s)) ? 'Required' : null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: _pickDeparture,
                  child: InputDecorator(
                    decoration: const InputDecoration(
                      labelText: 'Departure (your local time)',
                      prefixIcon: Icon(Icons.event),
                    ),
                    child: Text(
                      _departureLocal == null
                          ? 'Select date & time'
                          : DateFormat('EEE d MMM yyyy · HH:mm').format(_departureLocal!),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _first,
                      textCapitalization: TextCapitalization.words,
                      decoration: const InputDecoration(labelText: 'First name'),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _last,
                      textCapitalization: TextCapitalization.words,
                      decoration: const InputDecoration(labelText: 'Last name'),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline)),
                validator: (v) {
                  final s = (v ?? '').trim();
                  return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(s) ? null : 'Enter a valid email';
                },
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: theme.textTheme.bodyMedium?.copyWith(color: ConciergeColors.danger)),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _submitting ? null : _submit,
                child: _submitting
                    ? const SizedBox(
                        width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.black))
                    : Text(widget.submitLabel),
              ),
              const SizedBox(height: 4),
              TextButton(
                onPressed: _submitting ? null : () => Navigator.of(context).pop(),
                child: Text(widget.cancelLabel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FlightSummary extends StatelessWidget {
  const _FlightSummary({required this.offer});

  final FlightOffer offer;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final departs = DateFormat('EEE d MMM · HH:mm').format(offer.departureLocal);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ConciergeColors.surfaceHigh,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: ConciergeColors.outline),
      ),
      child: Row(
        children: [
          const Icon(Icons.flight_takeoff, color: ConciergeColors.gold),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${offer.airlineName} ${offer.flightNumber}',
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
                Text('${offer.origin} → ${offer.destination}  ·  departs $departs local',
                    style: theme.textTheme.bodySmall?.copyWith(color: ConciergeColors.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _UpperCaseFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) =>
      newValue.copyWith(text: newValue.text.toUpperCase());
}

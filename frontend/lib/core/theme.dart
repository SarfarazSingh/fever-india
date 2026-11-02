import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ConciergeColors {
  static const background = Color(0xFF0B0B0F);
  static const surface = Color(0xFF15151C);
  static const surfaceHigh = Color(0xFF1E1E27);
  static const outline = Color(0xFF2C2C38);
  static const gold = Color(0xFFC9A227);
  static const goldLight = Color(0xFFE6C766);
  static const goldDark = Color(0xFF8C6E12);
  static const textPrimary = Color(0xFFF3EFE6);
  static const textSecondary = Color(0xFFA19D93);
  static const success = Color(0xFF5BBF8A);
  static const danger = Color(0xFFE0675B);
  static const info = Color(0xFF6FA8DC);

  static const goldGradient = LinearGradient(
    colors: [goldLight, gold, goldDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

class ConciergeTheme {
  static ThemeData dark() {
    final base = ThemeData(useMaterial3: true, brightness: Brightness.dark);
    final body = GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: ConciergeColors.textPrimary,
      displayColor: ConciergeColors.textPrimary,
    );
    final display = GoogleFonts.playfairDisplayTextTheme(body);
    final textTheme = body.copyWith(
      displayLarge: display.displayLarge,
      displayMedium: display.displayMedium,
      displaySmall: display.displaySmall,
      headlineLarge: display.headlineLarge,
      headlineMedium: display.headlineMedium,
      headlineSmall: display.headlineSmall,
      titleLarge: display.titleLarge?.copyWith(fontWeight: FontWeight.w600),
    );

    const scheme = ColorScheme.dark(
      primary: ConciergeColors.gold,
      onPrimary: Colors.black,
      secondary: ConciergeColors.goldLight,
      onSecondary: Colors.black,
      surface: ConciergeColors.surface,
      onSurface: ConciergeColors.textPrimary,
      error: ConciergeColors.danger,
      outline: ConciergeColors.outline,
    );

    final inputBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: ConciergeColors.outline),
    );

    return base.copyWith(
      colorScheme: scheme,
      scaffoldBackgroundColor: ConciergeColors.background,
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: ConciergeColors.background,
        foregroundColor: ConciergeColors.textPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.headlineSmall?.copyWith(color: ConciergeColors.gold),
      ),
      cardTheme: CardThemeData(
        color: ConciergeColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: ConciergeColors.outline),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: ConciergeColors.surfaceHigh,
        labelStyle: const TextStyle(color: ConciergeColors.textSecondary),
        hintStyle: const TextStyle(color: ConciergeColors.textSecondary),
        prefixIconColor: ConciergeColors.gold,
        border: inputBorder,
        enabledBorder: inputBorder,
        focusedBorder: inputBorder.copyWith(
          borderSide: const BorderSide(color: ConciergeColors.gold, width: 1.4),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: ConciergeColors.gold,
          foregroundColor: Colors.black,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.4),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ConciergeColors.gold,
          side: const BorderSide(color: ConciergeColors.gold),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: ConciergeColors.gold),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: ConciergeColors.gold,
        foregroundColor: Colors.black,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: ConciergeColors.surface,
        indicatorColor: ConciergeColors.gold.withValues(alpha: 0.18),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? ConciergeColors.gold
                : ConciergeColors.textSecondary,
          ),
        ),
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: states.contains(WidgetState.selected)
                ? ConciergeColors.gold
                : ConciergeColors.textSecondary,
          ),
        ),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: ConciergeColors.surface,
        showDragHandle: true,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: ConciergeColors.surfaceHigh,
        contentTextStyle: TextStyle(color: ConciergeColors.textPrimary),
        behavior: SnackBarBehavior.floating,
      ),
      dividerTheme: const DividerThemeData(color: ConciergeColors.outline, thickness: 1),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: ConciergeColors.gold),
      datePickerTheme: const DatePickerThemeData(
        backgroundColor: ConciergeColors.surface,
        headerBackgroundColor: ConciergeColors.surfaceHigh,
        headerForegroundColor: ConciergeColors.gold,
      ),
    );
  }
}

import 'package:flutter_test/flutter_test.dart';

import 'package:deepagent_app/main.dart';

void main() {
  testWidgets('DeepAgent app loads', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const DeepAgentApp());

    // Verify that the app title is displayed in AppBar.
    expect(find.text('DeepAgent'), findsOneWidget);

    // Verify the New Task FAB is present.
    expect(find.text('New Task'), findsOneWidget);
  });
}

import SwiftUI

public struct ScreenAwakeState {
  public private(set) var enabled = false
  public init() {}
  public mutating func toggle() { enabled.toggle() }
  /// Closing or leaving the foreground cancels the request, rather than resuming it later.
  public mutating func deactivate() { enabled = false }
}

public struct KeepScreenOnButton: View {
  @Environment(\.scenePhase) private var scenePhase
  @State private var state = ScreenAwakeState()
  @StateObject private var wake = CookingWakeController()
  public init() {}
  public var body: some View {
    Button {
      state.toggle()
      wake.setEnabled(state.enabled && scenePhase == .active)
    } label: {
      Label("Keep screen on", systemImage: state.enabled ? "sun.max.fill" : "sun.max")
    }
    .foregroundStyle(state.enabled ? Color.accentColor : Color.primary)
    .accessibilityValue(state.enabled ? "On" : "Off")
    .help(state.enabled ? "Turn off Keep screen on" : "Keep the display awake while this recipe is open")
    .onChange(of: scenePhase) { phase in
      if phase != .active { state.deactivate(); wake.setEnabled(false) }
    }
    .onDisappear { state.deactivate(); wake.setEnabled(false) }
  }
}

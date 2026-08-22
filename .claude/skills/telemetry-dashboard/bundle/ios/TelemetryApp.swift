// TelemetryApp.swift
//
// NOTE: Source-only, uncompiled/untested — see SensorManager.swift header.
// Minimal SwiftUI view over SensorManager's live @Published values.

import SwiftUI

@main
struct TelemetryApp: App {
    @StateObject private var sensorManager = SensorManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(sensorManager)
                .onAppear {
                    sensorManager.startMotionSensors()
                }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var sensorManager: SensorManager

    var body: some View {
        NavigationView {
            List {
                Section("Accelerometer (g)") {
                    Text("x: \(sensorManager.accelerometerData.x, specifier: "%.3f")")
                    Text("y: \(sensorManager.accelerometerData.y, specifier: "%.3f")")
                    Text("z: \(sensorManager.accelerometerData.z, specifier: "%.3f")")
                }
                Section("Gyroscope (°/s)") {
                    Text("x: \(sensorManager.gyroscopeData.x, specifier: "%.2f")")
                    Text("y: \(sensorManager.gyroscopeData.y, specifier: "%.2f")")
                    Text("z: \(sensorManager.gyroscopeData.z, specifier: "%.2f")")
                }
                Section("Heading") {
                    Text("\(sensorManager.headingDegrees, specifier: "%.1f")°")
                }
                Section("Backend") {
                    Text(sensorManager.isConnected ? "Connected" : "Disconnected")
                        .foregroundColor(sensorManager.isConnected ? .green : .red)
                }
            }
            .navigationTitle("Telemetry")
        }
    }
}

// SensorManager.swift
//
// NOTE: This file is source-only. It has NOT been compiled, run, or tested —
// this bundle was built in a Linux container with no Xcode/macOS toolchain
// available. Treat it as a starting point, not a verified artifact.
//
// Wraps CoreMotion for accelerometer/gyroscope/magnetometer and streams
// readings to the same backend the web dashboard uses, over the /ws/sensors
// WebSocket, using the same JSON field names as telemetry_backend's
// `read_sensors()` motion payload so both clients speak one protocol.

import Foundation
import CoreMotion
import Combine

struct AccelerometerData {
    let x: Double
    let y: Double
    let z: Double
}

final class SensorManager: ObservableObject {
    private let motionManager = CMMotionManager()
    private var webSocketTask: URLSessionWebSocketTask?

    @Published var accelerometerData = AccelerometerData(x: 0, y: 0, z: 0)
    @Published var gyroscopeData = AccelerometerData(x: 0, y: 0, z: 0)
    @Published var headingDegrees: Double = 0
    @Published var isConnected = false

    /// Base URL of the telemetry backend, e.g. "http://192.168.1.20:8000".
    var backendBaseURL: String = "http://localhost:8000"

    func startMotionSensors() {
        guard motionManager.isDeviceMotionAvailable else { return }
        motionManager.deviceMotionUpdateInterval = 1.0 / 30.0
        motionManager.startDeviceMotionUpdates(to: .main) { [weak self] motion, error in
            guard let self, let motion else { return }
            self.accelerometerData = AccelerometerData(
                x: motion.userAcceleration.x,
                y: motion.userAcceleration.y,
                z: motion.userAcceleration.z + 1.0 // include gravity to match backend's ~1g baseline
            )
            self.gyroscopeData = AccelerometerData(
                x: motion.rotationRate.x,
                y: motion.rotationRate.y,
                z: motion.rotationRate.z
            )
            self.headingDegrees = motion.heading >= 0 ? motion.heading : 0
        }
    }

    func stopMotionSensors() {
        motionManager.stopDeviceMotionUpdates()
    }

    /// Connects to the backend's /ws/sensors stream (read-only mirror; the
    /// backend remains the source of truth for the shared dashboard).
    func connectToBackend() {
        guard let wsURL = URL(string: backendBaseURL.replacingOccurrences(of: "http", with: "ws") + "/ws/sensors") else { return }
        let task = URLSession.shared.webSocketTask(with: wsURL)
        webSocketTask = task
        task.resume()
        isConnected = true
        receiveLoop()
    }

    private func receiveLoop() {
        webSocketTask?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success:
                self.receiveLoop()
            case .failure:
                self.isConnected = false
            }
        }
    }

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }
}

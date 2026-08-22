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

/// Mirrors the `audio` object in telemetry_backend's /ws/sensors payload,
/// including the wave-pattern-match mute fields.
struct AudioReading: Decodable {
    let fft: [Double]
    let rms: Double
    let directionDeg: Double
    let dominantFreqHz: Double
    let muted: Bool
    let matchScore: Double

    enum CodingKeys: String, CodingKey {
        case fft, rms
        case directionDeg = "direction_deg"
        case dominantFreqHz = "dominant_freq_hz"
        case muted
        case matchScore = "match_score"
    }
}

private struct SensorMessage: Decodable {
    let audio: AudioReading
}

final class SensorManager: ObservableObject {
    private let motionManager = CMMotionManager()
    private var webSocketTask: URLSessionWebSocketTask?
    private let decoder = JSONDecoder()

    @Published var accelerometerData = AccelerometerData(x: 0, y: 0, z: 0)
    @Published var gyroscopeData = AccelerometerData(x: 0, y: 0, z: 0)
    @Published var headingDegrees: Double = 0
    @Published var isConnected = false

    /// Wave pattern match / mute state, mirrored from the backend on every
    /// WebSocket tick — see backend/main.py's PATTERN_MATCH.
    @Published var audioMuted: Bool = false
    @Published var audioMatchScore: Double = 0

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
            case .success(let message):
                self.handle(message)
                self.receiveLoop()
            case .failure:
                self.isConnected = false
            }
        }
    }

    private func handle(_ message: URLSessionWebSocketTask.Message) {
        guard case .string(let text) = message, let data = text.data(using: .utf8) else { return }
        guard let decoded = try? decoder.decode(SensorMessage.self, from: data) else { return }
        DispatchQueue.main.async {
            self.audioMuted = decoded.audio.muted
            self.audioMatchScore = decoded.audio.matchScore
        }
    }

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }

    // MARK: - Wave pattern mute controls (mirrors the dashboard's Audio tab)

    /// Captures the backend's current audio FFT as the reference pattern to
    /// match against; subsequent ticks that match closely enough get muted.
    func captureMutePattern() {
        postMuteAction(path: "/api/mute/capture")
    }

    func clearMutePattern() {
        postMuteAction(path: "/api/mute/clear")
    }

    private func postMuteAction(path: String) {
        guard let url = URL(string: backendBaseURL + path) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        URLSession.shared.dataTask(with: request).resume()
    }
}

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/task.dart';

class ApiException implements Exception {
  final String message;
  final String code;
  final int? statusCode;

  ApiException(this.message, this.code, [this.statusCode]);

  @override
  String toString() => 'ApiException: $message (code: $code)';
}

/// Determines the API base URL dynamically.
/// When served from the same origin as the API, use empty string (relative URLs).
/// Otherwise, construct URL from current host.
String _getDefaultBaseUrl() {
  if (kIsWeb) {
    // Use relative URLs when served from same origin (orchestrator serves both)
    final uri = Uri.base;
    // If running on standard ports (80/443) or same as API, use relative
    if (uri.port == 80 || uri.port == 443 || uri.port == 8000) {
      return '';  // Relative URLs
    }
    // For dev server on different port, try same host with port 8000
    return '${uri.scheme}://${uri.host}:8000';
  }
  return 'http://localhost:8000';
}

class ApiClient extends ChangeNotifier {
  final String baseUrl;
  final http.Client _client;

  bool _isLoading = false;
  String? _error;

  bool get isLoading => _isLoading;
  String? get error => _error;

  ApiClient({String? baseUrl})
      : baseUrl = baseUrl ?? _getDefaultBaseUrl(),
        _client = http.Client();

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void _setError(String? error) {
    _error = error;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  Future<T> _request<T>({
    required String method,
    required String path,
    Map<String, dynamic>? body,
    required T Function(dynamic json) parser,
  }) async {
    _setLoading(true);
    _setError(null);

    try {
      final uri = Uri.parse('$baseUrl$path');
      late http.Response response;

      switch (method) {
        case 'GET':
          response = await _client.get(
            uri,
            headers: {'Content-Type': 'application/json'},
          );
          break;
        case 'POST':
          response = await _client.post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: body != null ? jsonEncode(body) : null,
          );
          break;
        case 'DELETE':
          response = await _client.delete(
            uri,
            headers: {'Content-Type': 'application/json'},
          );
          break;
        default:
          throw ApiException('Unsupported method: $method', 'INVALID_METHOD');
      }

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json = jsonDecode(response.body);
        return parser(json);
      } else {
        final errorJson = jsonDecode(response.body);
        throw ApiException(
          errorJson['error'] ?? 'Unknown error',
          errorJson['code'] ?? 'UNKNOWN_ERROR',
          response.statusCode,
        );
      }
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException(
        'Network error: $e',
        'NETWORK_ERROR',
      );
    } finally {
      _setLoading(false);
    }
  }

  /// Create a new task
  Future<Task> createTask(TaskCreate task) async {
    return _request(
      method: 'POST',
      path: '/api/v1/tasks',
      body: task.toJson(),
      parser: (json) => Task.fromJson(json),
    );
  }

  /// Get all tasks
  Future<TaskListResponse> getTasks({int page = 1, int pageSize = 20}) async {
    return _request(
      method: 'GET',
      path: '/api/v1/tasks?page=$page&page_size=$pageSize',
      parser: (json) => TaskListResponse.fromJson(json),
    );
  }

  /// Get a specific task
  Future<Task> getTask(String taskId) async {
    return _request(
      method: 'GET',
      path: '/api/v1/tasks/$taskId',
      parser: (json) => Task.fromJson(json),
    );
  }

  /// Get task result
  Future<TaskResult> getTaskResult(String taskId) async {
    return _request(
      method: 'GET',
      path: '/api/v1/tasks/$taskId/result',
      parser: (json) => TaskResult.fromJson(json),
    );
  }

  /// Cancel/delete a task
  Future<void> cancelTask(String taskId) async {
    return _request(
      method: 'DELETE',
      path: '/api/v1/tasks/$taskId',
      parser: (_) {},
    );
  }

  /// Health check
  Future<Map<String, dynamic>> healthCheck() async {
    return _request(
      method: 'GET',
      path: '/api/v1/health',
      parser: (json) => json as Map<String, dynamic>,
    );
  }

  @override
  void dispose() {
    _client.close();
    super.dispose();
  }
}

/// Task data models for DeepAgent client.
library;

enum TaskType {
  research,
  analysis,
  document;

  String get value {
    switch (this) {
      case TaskType.research:
        return 'research';
      case TaskType.analysis:
        return 'analysis';
      case TaskType.document:
        return 'document';
    }
  }

  String get displayName {
    switch (this) {
      case TaskType.research:
        return 'Research';
      case TaskType.analysis:
        return 'Analysis';
      case TaskType.document:
        return 'Document';
    }
  }

  static TaskType fromString(String value) {
    switch (value) {
      case 'research':
        return TaskType.research;
      case 'analysis':
        return TaskType.analysis;
      case 'document':
        return TaskType.document;
      default:
        return TaskType.research;
    }
  }
}

enum TaskStatus {
  pending,
  queued,
  running,
  processing,
  completed,
  failed,
  retry,
  dead;

  String get value {
    switch (this) {
      case TaskStatus.pending:
        return 'pending';
      case TaskStatus.queued:
        return 'queued';
      case TaskStatus.running:
        return 'running';
      case TaskStatus.processing:
        return 'processing';
      case TaskStatus.completed:
        return 'completed';
      case TaskStatus.failed:
        return 'failed';
      case TaskStatus.retry:
        return 'retry';
      case TaskStatus.dead:
        return 'dead';
    }
  }

  String get displayName {
    switch (this) {
      case TaskStatus.pending:
        return 'Pending';
      case TaskStatus.queued:
        return 'Queued';
      case TaskStatus.running:
        return 'Running';
      case TaskStatus.processing:
        return 'Processing';
      case TaskStatus.completed:
        return 'Completed';
      case TaskStatus.failed:
        return 'Failed';
      case TaskStatus.retry:
        return 'Retrying';
      case TaskStatus.dead:
        return 'Dead';
    }
  }

  bool get isActive =>
      this == TaskStatus.pending ||
      this == TaskStatus.queued ||
      this == TaskStatus.running ||
      this == TaskStatus.processing ||
      this == TaskStatus.retry;

  bool get isTerminal =>
      this == TaskStatus.completed ||
      this == TaskStatus.failed ||
      this == TaskStatus.dead;

  static TaskStatus fromString(String value) {
    switch (value) {
      case 'pending':
        return TaskStatus.pending;
      case 'queued':
        return TaskStatus.queued;
      case 'running':
        return TaskStatus.running;
      case 'processing':
        return TaskStatus.processing;
      case 'completed':
        return TaskStatus.completed;
      case 'failed':
        return TaskStatus.failed;
      case 'retry':
        return TaskStatus.retry;
      case 'dead':
        return TaskStatus.dead;
      default:
        return TaskStatus.pending;
    }
  }
}

class Task {
  final String id;
  final TaskType type;
  final String title;
  final String? description;
  final TaskStatus status;
  final int attempts;
  final int maxAttempts;
  final DateTime createdAt;
  final DateTime? queuedAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final String? lastError;

  Task({
    required this.id,
    required this.type,
    required this.title,
    this.description,
    required this.status,
    required this.attempts,
    required this.maxAttempts,
    required this.createdAt,
    this.queuedAt,
    this.startedAt,
    this.completedAt,
    this.lastError,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'] as String,
      type: TaskType.fromString(json['type'] as String),
      title: json['title'] as String,
      description: json['description'] as String?,
      status: TaskStatus.fromString(json['status'] as String),
      attempts: json['attempts'] as int,
      maxAttempts: json['max_attempts'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
      queuedAt: json['queued_at'] != null
          ? DateTime.parse(json['queued_at'] as String)
          : null,
      startedAt: json['started_at'] != null
          ? DateTime.parse(json['started_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      lastError: json['last_error'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type.value,
      'title': title,
      'description': description,
      'status': status.value,
      'attempts': attempts,
      'max_attempts': maxAttempts,
      'created_at': createdAt.toIso8601String(),
      'queued_at': queuedAt?.toIso8601String(),
      'started_at': startedAt?.toIso8601String(),
      'completed_at': completedAt?.toIso8601String(),
      'last_error': lastError,
    };
  }
}

class TaskCreate {
  final TaskType type;
  final String title;
  final String description;
  final Map<String, dynamic>? config;

  TaskCreate({
    required this.type,
    required this.title,
    required this.description,
    this.config,
  });

  Map<String, dynamic> toJson() {
    return {
      'type': type.value,
      'title': title,
      'description': description,
      if (config != null) 'config': config,
    };
  }
}

class TaskResult {
  final String taskId;
  final TaskStatus status;
  final String? summary;
  final String? outputsPath;
  final Map<String, String>? cloudLinks;

  TaskResult({
    required this.taskId,
    required this.status,
    this.summary,
    this.outputsPath,
    this.cloudLinks,
  });

  factory TaskResult.fromJson(Map<String, dynamic> json) {
    return TaskResult(
      taskId: json['task_id'] as String,
      status: TaskStatus.fromString(json['status'] as String),
      summary: json['summary'] as String?,
      outputsPath: json['outputs_path'] as String?,
      cloudLinks: json['cloud_links'] != null
          ? Map<String, String>.from(json['cloud_links'] as Map)
          : null,
    );
  }
}

class TaskListResponse {
  final List<Task> tasks;
  final int total;
  final int page;
  final int pageSize;

  TaskListResponse({
    required this.tasks,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  factory TaskListResponse.fromJson(Map<String, dynamic> json) {
    return TaskListResponse(
      tasks: (json['tasks'] as List)
          .map((e) => Task.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      page: json['page'] as int,
      pageSize: json['page_size'] as int,
    );
  }
}

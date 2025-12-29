import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/task.dart';
import '../services/api_client.dart';

class TaskDetailScreen extends StatefulWidget {
  final ApiClient apiClient;
  final String taskId;

  const TaskDetailScreen({
    super.key,
    required this.apiClient,
    required this.taskId,
  });

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  Task? _task;
  TaskResult? _result;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTask();
  }

  Future<void> _loadTask() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final task = await widget.apiClient.getTask(widget.taskId);
      setState(() {
        _task = task;
      });

      if (task.status == TaskStatus.completed ||
          task.status == TaskStatus.failed ||
          task.status == TaskStatus.dead) {
        try {
          final result = await widget.apiClient.getTaskResult(widget.taskId);
          setState(() {
            _result = result;
          });
        } catch (_) {
          // Result might not be available
        }
      }

      setState(() {
        _isLoading = false;
      });
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to load task: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _cancelTask() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Task'),
        content: const Text('Are you sure you want to cancel this task?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Yes, Cancel'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await widget.apiClient.cancelTask(widget.taskId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Task cancelled'),
            backgroundColor: Colors.orange,
          ),
        );
        Navigator.pop(context);
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.message}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Task Details'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadTask,
            tooltip: 'Refresh',
          ),
          if (_task != null && _task!.status.isActive)
            IconButton(
              icon: const Icon(Icons.cancel),
              onPressed: _cancelTask,
              tooltip: 'Cancel Task',
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _error!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadTask,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_task == null) {
      return const Center(child: Text('Task not found'));
    }

    return RefreshIndicator(
      onRefresh: _loadTask,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: 24),
            _buildStatusCard(),
            const SizedBox(height: 16),
            _buildTimestampsCard(),
            if (_task!.lastError != null) ...[
              const SizedBox(height: 16),
              _buildErrorCard(),
            ],
            if (_result?.summary != null) ...[
              const SizedBox(height: 16),
              _buildResultCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _buildTypeBadge(),
            const SizedBox(width: 8),
            _buildStatusBadge(),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          _task!.title,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        if (_task!.description != null) ...[
          const SizedBox(height: 8),
          Text(
            _task!.description!,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: Theme.of(context).colorScheme.outline,
                ),
          ),
        ],
      ],
    );
  }

  Widget _buildTypeBadge() {
    final color = _getTypeColor();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_getTypeIcon(), size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            _task!.type.displayName,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    final color = _getStatusColor();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_task!.status.isActive)
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2, color: color),
            )
          else
            Icon(_getStatusIcon(), size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            _task!.status.displayName,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Status',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            _buildStatusRow(
              'Attempts',
              '${_task!.attempts} / ${_task!.maxAttempts}',
              Icons.replay,
            ),
            const SizedBox(height: 12),
            _buildStatusRow(
              'Task ID',
              _task!.id,
              Icons.tag,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimestampsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Timeline',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            _buildTimestampRow('Created', _task!.createdAt, true),
            if (_task!.queuedAt != null)
              _buildTimestampRow('Queued', _task!.queuedAt!, true),
            if (_task!.startedAt != null)
              _buildTimestampRow('Started', _task!.startedAt!, true),
            if (_task!.completedAt != null)
              _buildTimestampRow('Completed', _task!.completedAt!, false),
          ],
        ),
      ),
    );
  }

  Widget _buildTimestampRow(String label, DateTime time, bool showLine) {
    final dateFormat = DateFormat.yMMMd().add_jm();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                shape: BoxShape.circle,
              ),
            ),
            if (showLine)
              Container(
                width: 2,
                height: 32,
                color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3),
              ),
          ],
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: showLine ? 20 : 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Text(
                  dateFormat.format(time.toLocal()),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.outline,
                      ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildErrorCard() {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.error, color: Colors.red.shade700),
                const SizedBox(width: 8),
                Text(
                  'Error',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: Colors.red.shade700,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _task!.lastError!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.red.shade900,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    return Card(
      color: Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green.shade700),
                const SizedBox(width: 8),
                Text(
                  'Result Summary',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: Colors.green.shade700,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _result!.summary!,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (_result!.outputsPath != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.folder, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _result!.outputsPath!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontFamily: 'monospace',
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).colorScheme.outline),
        const SizedBox(width: 12),
        Text(
          label,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.outline,
              ),
        ),
        const Spacer(),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
        ),
      ],
    );
  }

  IconData _getTypeIcon() {
    switch (_task!.type) {
      case TaskType.research:
        return Icons.search;
      case TaskType.analysis:
        return Icons.analytics;
      case TaskType.document:
        return Icons.description;
    }
  }

  Color _getTypeColor() {
    switch (_task!.type) {
      case TaskType.research:
        return Colors.blue;
      case TaskType.analysis:
        return Colors.orange;
      case TaskType.document:
        return Colors.green;
    }
  }

  IconData _getStatusIcon() {
    switch (_task!.status) {
      case TaskStatus.pending:
        return Icons.hourglass_empty;
      case TaskStatus.queued:
        return Icons.queue;
      case TaskStatus.running:
        return Icons.play_arrow;
      case TaskStatus.processing:
        return Icons.sync;
      case TaskStatus.completed:
        return Icons.check_circle;
      case TaskStatus.failed:
        return Icons.error;
      case TaskStatus.retry:
        return Icons.replay;
      case TaskStatus.dead:
        return Icons.cancel;
    }
  }

  Color _getStatusColor() {
    switch (_task!.status) {
      case TaskStatus.pending:
      case TaskStatus.queued:
        return Colors.grey;
      case TaskStatus.running:
      case TaskStatus.processing:
        return Colors.blue;
      case TaskStatus.completed:
        return Colors.green;
      case TaskStatus.failed:
      case TaskStatus.dead:
        return Colors.red;
      case TaskStatus.retry:
        return Colors.orange;
    }
  }
}

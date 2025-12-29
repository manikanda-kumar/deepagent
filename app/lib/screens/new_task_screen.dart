import 'package:flutter/material.dart';
import '../models/task.dart';
import '../services/api_client.dart';

class NewTaskScreen extends StatefulWidget {
  final ApiClient apiClient;

  const NewTaskScreen({super.key, required this.apiClient});

  @override
  State<NewTaskScreen> createState() => _NewTaskScreenState();
}

class _NewTaskScreenState extends State<NewTaskScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();

  TaskType _selectedType = TaskType.research;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submitTask() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      final task = TaskCreate(
        type: _selectedType,
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
      );

      await widget.apiClient.createTask(task);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Task created successfully'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context, true);
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
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('New Task'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildTypeSelector(),
              const SizedBox(height: 24),
              _buildTitleField(),
              const SizedBox(height: 16),
              _buildDescriptionField(),
              const SizedBox(height: 32),
              _buildSubmitButton(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypeSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Task Type',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: 8),
        SegmentedButton<TaskType>(
          segments: [
            ButtonSegment(
              value: TaskType.research,
              icon: const Icon(Icons.search),
              label: const Text('Research'),
            ),
            ButtonSegment(
              value: TaskType.analysis,
              icon: const Icon(Icons.analytics),
              label: const Text('Analysis'),
            ),
            ButtonSegment(
              value: TaskType.document,
              icon: const Icon(Icons.description),
              label: const Text('Document'),
            ),
          ],
          selected: {_selectedType},
          onSelectionChanged: (selection) {
            setState(() {
              _selectedType = selection.first;
            });
          },
        ),
        const SizedBox(height: 8),
        Text(
          _getTypeDescription(),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.outline,
              ),
        ),
      ],
    );
  }

  String _getTypeDescription() {
    switch (_selectedType) {
      case TaskType.research:
        return 'Deep research on a topic with web search and source citations';
      case TaskType.analysis:
        return 'Analyze data, trends, or content from various sources';
      case TaskType.document:
        return 'Generate documents, reports, or summaries';
    }
  }

  Widget _buildTitleField() {
    return TextFormField(
      controller: _titleController,
      decoration: const InputDecoration(
        labelText: 'Title',
        hintText: 'Enter a descriptive title for your task',
        border: OutlineInputBorder(),
        prefixIcon: Icon(Icons.title),
      ),
      maxLength: 200,
      textInputAction: TextInputAction.next,
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return 'Please enter a title';
        }
        if (value.trim().length < 3) {
          return 'Title must be at least 3 characters';
        }
        return null;
      },
    );
  }

  Widget _buildDescriptionField() {
    return TextFormField(
      controller: _descriptionController,
      decoration: InputDecoration(
        labelText: 'Description',
        hintText: _getDescriptionHint(),
        border: const OutlineInputBorder(),
        alignLabelWithHint: true,
        prefixIcon: const Padding(
          padding: EdgeInsets.only(bottom: 80),
          child: Icon(Icons.notes),
        ),
      ),
      maxLines: 5,
      maxLength: 2000,
      textInputAction: TextInputAction.newline,
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return 'Please enter a description';
        }
        if (value.trim().length < 10) {
          return 'Description must be at least 10 characters';
        }
        return null;
      },
    );
  }

  String _getDescriptionHint() {
    switch (_selectedType) {
      case TaskType.research:
        return 'Describe what you want to research. Be specific about topics, questions, and desired depth.';
      case TaskType.analysis:
        return 'Describe what you want to analyze. Include data sources, metrics, and analysis goals.';
      case TaskType.document:
        return 'Describe the document you want to generate. Include format, structure, and content requirements.';
    }
  }

  Widget _buildSubmitButton() {
    return FilledButton.icon(
      onPressed: _isSubmitting ? null : _submitTask,
      icon: _isSubmitting
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : const Icon(Icons.send),
      label: Text(_isSubmitting ? 'Creating...' : 'Create Task'),
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    );
  }
}

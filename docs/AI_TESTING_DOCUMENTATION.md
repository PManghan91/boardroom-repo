# AI Operations Testing Suite Documentation

This document provides comprehensive documentation for the AI operations testing suite, covering test strategy, implementation, and usage guidelines.

## Table of Contents

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Test Categories](#test-categories)
4. [Running Tests](#running-tests)
5. [Test Implementation Guide](#test-implementation-guide)
6. [CI/CD Integration](#cicd-integration)
7. [Coverage Requirements](#coverage-requirements)
8. [Performance Benchmarks](#performance-benchmarks)
9. [Troubleshooting](#troubleshooting)

## Overview

The AI operations testing suite provides comprehensive testing coverage for all AI-related modules in the boardroom application, ensuring reliability, performance, and security of AI operations.

### Key Objectives

- **Coverage**: Achieve 80%+ test coverage for all AI modules
- **Reliability**: Ensure AI operations work correctly under various conditions
- **Performance**: Validate response times and resource usage
- **Security**: Verify AI operations are secure and handle edge cases
- **Integration**: Test API endpoints and service interactions

### Tested Components

- **LangGraph Agent** (`app/core/langgraph/graph.py`)
- **Meeting Management Tools** (`app/core/langgraph/tools/meeting_management.py`)
- **AI State Manager** (`app/services/ai_state_manager.py`)
- **AI Operations API** (`app/api/v1/ai_operations.py`)

## Test Architecture

### Directory Structure

```
tests/
├── unit/                           # Unit tests for individual modules
│   ├── test_langgraph_graph.py    # LangGraph agent tests
│   ├── test_meeting_management_tools.py # Meeting tools tests
│   └── test_ai_state_manager.py   # State manager tests
├── integration/                    # Integration tests
│   └── test_ai_operations_endpoints.py # API endpoint tests
├── performance/                    # Performance and load tests
│   └── test_ai_operations_performance.py
└── fixtures/                      # Test data and fixtures
    └── ai_fixtures.py
```

### Test Categories

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test API endpoints and service interactions
3. **Performance Tests**: Test response times and resource usage
4. **Security Tests**: Test for vulnerabilities and edge cases
5. **Load Tests**: Test behavior under high concurrent load

## Test Categories

### Unit Tests

#### LangGraph Agent Tests (`test_langgraph_graph.py`)

**Purpose**: Test core AI agent functionality including LLM interaction, tool execution, and conversation management.

**Key Test Areas**:
- Agent initialization and configuration
- LLM response generation and streaming
- Tool execution and error handling
- Chat history management
- Graph workflow execution
- Error recovery and fallback mechanisms

**Example Test**:
```python
@pytest.mark.asyncio
async def test_agent_chat_response(agent, mock_llm):
    """Test basic chat response generation."""
    query = "What is the meeting agenda?"
    
    response = await agent.chat(query)
    
    assert response is not None
    assert isinstance(response, str)
    mock_llm.ainvoke.assert_called_once()
```

#### Meeting Management Tools Tests (`test_meeting_management_tools.py`)

**Purpose**: Test individual meeting management tools for functionality and error handling.

**Key Test Areas**:
- Agenda creation with various inputs
- Decision support analysis
- Meeting minutes generation
- Input validation and sanitization
- Error handling for invalid inputs
- Metrics tracking and logging

**Coverage**: 95%+ for all tool classes and methods

#### AI State Manager Tests (`test_ai_state_manager.py`)

**Purpose**: Test conversation state management, persistence, and concurrency handling.

**Key Test Areas**:
- State creation and initialization
- State updates and versioning
- Checkpoint creation and restoration
- Concurrent access handling
- State cleanup and expiration
- Error recovery mechanisms

### Integration Tests

#### AI Operations Endpoints (`test_ai_operations_endpoints.py`)

**Purpose**: Test AI operations API endpoints end-to-end with authentication and error handling.

**Key Test Areas**:
- Health check endpoints
- Session management operations
- Checkpoint creation and restoration
- Metrics collection and reporting
- Authentication and authorization
- Error response formatting

**Test Classes**:
- `TestAIOperationsEndpoints`: Basic endpoint functionality
- `TestAIOperationsAuthentication`: Authentication requirements
- `TestAIOperationsEndToEnd`: Complete workflows
- `TestAIOperationsPerformance`: Response time validation

### Performance Tests

#### AI Operations Performance (`test_ai_operations_performance.py`)

**Purpose**: Validate performance characteristics of AI operations under various load conditions.

**Key Test Areas**:
- Response time benchmarks
- Memory usage analysis
- Concurrent request handling
- Sustained load performance
- Resource exhaustion handling
- Throughput measurement

**Performance Targets**:
- Single query response: < 500ms
- Agent initialization: < 100ms
- State operations: < 50ms
- Concurrent requests: Handle 50+ simultaneous
- Memory usage: < 200MB for 100 operations

## Running Tests

### Quick Start

```bash
# Run all AI tests
python scripts/run_ai_tests.py

# Run specific module tests
python scripts/run_ai_tests.py --module langgraph

# Run with performance tests
python scripts/run_ai_tests.py --performance

# Run complete suite
python scripts/run_ai_tests.py --full
```

### Manual Test Execution

#### Unit Tests
```bash
# All unit tests
pytest tests/unit/ -v

# Specific module
pytest tests/unit/test_langgraph_graph.py -v

# With coverage
pytest tests/unit/ --cov=app.core.langgraph --cov-report=html
```

#### Integration Tests
```bash
# All integration tests
pytest tests/integration/ -v

# AI operations endpoints only
pytest tests/integration/test_ai_operations_endpoints.py -v

# Skip slow tests
pytest tests/integration/ -m "not slow" -v
```

#### Performance Tests
```bash
# Performance tests only
pytest tests/performance/ -m "performance" -v

# Including load tests
pytest tests/performance/ -m "performance" -v --maxfail=3

# Specific performance category
pytest tests/performance/ -k "response_time" -v
```

### Test Runner Script

The dedicated test runner (`scripts/run_ai_tests.py`) provides:

- **Environment setup**: Automatic test environment configuration
- **Comprehensive reporting**: JSON and Markdown reports
- **Coverage analysis**: Combined coverage reporting
- **Security scanning**: Bandit and Safety integration
- **Performance benchmarking**: Response time and resource analysis

**Usage Examples**:
```bash
# Standard test run
python scripts/run_ai_tests.py

# Full test suite with performance and security
python scripts/run_ai_tests.py --full

# Only unit tests for specific module
python scripts/run_ai_tests.py --module ai_state_manager --skip-integration

# Performance tests only
python scripts/run_ai_tests.py --performance --skip-unit --skip-integration
```

## Test Implementation Guide

### Writing Unit Tests

#### Test Structure Template
```python
@pytest.mark.asyncio
class TestComponentName:
    """Test class for ComponentName."""
    
    @pytest.fixture
    def mock_dependency(self):
        """Create mock for external dependency."""
        return AsyncMock()
    
    @pytest.fixture
    def component(self, mock_dependency):
        """Create component instance for testing."""
        with patch('module.dependency', mock_dependency):
            return ComponentName()
    
    @pytest.mark.asyncio
    async def test_method_success(self, component):
        """Test successful method execution."""
        # Arrange
        input_data = {"test": "data"}
        
        # Act
        result = await component.method(input_data)
        
        # Assert
        assert result is not None
        assert result.success is True
```

#### Mocking Guidelines

1. **Mock External Dependencies**: Always mock LLM calls, database operations, and external APIs
2. **Use Realistic Mock Data**: Mock responses should reflect real data structures
3. **Control Timing**: Use controlled delays in mocks for performance tests
4. **Mock Failures**: Test error conditions with mocked exceptions

#### Error Testing Patterns
```python
@pytest.mark.asyncio
async def test_method_handles_llm_error(self, component, mock_llm):
    """Test error handling for LLM failures."""
    mock_llm.ainvoke.side_effect = Exception("LLM error")
    
    with pytest.raises(AIOperationError):
        await component.method("test input")
```

### Writing Integration Tests

#### API Testing Template
```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIEndpoints:
    """Integration tests for API endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_endpoint_success(self, client, auth_headers):
        """Test successful endpoint response."""
        response = await client.get("/ai/endpoint", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

### Writing Performance Tests

#### Performance Test Template
```python
@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformance:
    """Performance tests for AI operations."""
    
    @pytest.mark.asyncio
    async def test_response_time(self, component):
        """Test response time performance."""
        start_time = time.time()
        
        result = await component.operation()
        
        response_time = time.time() - start_time
        assert response_time < 0.5  # 500ms threshold
        assert result is not None
```

## CI/CD Integration

### GitHub Actions Workflow

The AI testing suite is integrated with GitHub Actions for automated testing on:

- **Push events**: To main, develop, and task branches
- **Pull requests**: To main and develop branches
- **Scheduled runs**: Nightly at 2 AM UTC
- **Manual triggers**: With configurable test levels

### Workflow Jobs

1. **Quality Gates**: Linting, type checking, and change detection
2. **Unit Tests**: Parallel execution across test groups
3. **Integration Tests**: With database and Redis services
4. **Performance Tests**: Conditional on schedule or manual trigger
5. **Security Tests**: Bandit and Safety scans
6. **Coverage Report**: Aggregated coverage analysis

### Quality Gates

- **Code Quality**: Ruff linting and formatting
- **Type Safety**: MyPy type checking
- **Coverage Threshold**: 80% minimum coverage
- **Security**: Clean Bandit and Safety reports

## Coverage Requirements

### Target Coverage Levels

- **Overall AI Modules**: 80% minimum
- **Critical Components**: 90% minimum
  - LangGraph Agent core methods
  - AI State Manager operations
  - Meeting tools execution paths
- **API Endpoints**: 85% minimum
- **Error Handling**: 95% minimum

### Coverage Measurement

```bash
# Generate coverage report
pytest --cov=app.core.langgraph --cov=app.services.ai_state_manager --cov-report=html

# Check coverage threshold
coverage report --fail-under=80

# Combine multiple coverage reports
coverage combine coverage-*.xml
```

### Coverage Exclusions

- Debug and development-only code
- Platform-specific code paths
- Deprecated functions marked for removal

## Performance Benchmarks

### Response Time Targets

| Operation | Target | Threshold |
|-----------|--------|-----------|
| Agent initialization | < 100ms | 200ms |
| Single chat query | < 500ms | 1000ms |
| Tool execution | < 200ms | 500ms |
| State operation | < 50ms | 100ms |
| API endpoint | < 300ms | 600ms |

### Throughput Targets

| Scenario | Target | Minimum |
|----------|--------|---------|
| Concurrent queries | 50 req/s | 25 req/s |
| State operations | 100 ops/s | 50 ops/s |
| API requests | 100 req/s | 50 req/s |

### Resource Usage Limits

- **Memory**: < 200MB per 100 operations
- **CPU**: Efficient utilization during concurrent operations
- **Database**: Minimal query count and optimized queries

## Troubleshooting

### Common Test Issues

#### 1. Mock Configuration Errors
```
Error: Mock object has no attribute 'ainvoke'
```
**Solution**: Ensure async mocks are properly configured:
```python
mock_llm = AsyncMock()
mock_llm.ainvoke = AsyncMock(return_value=Mock(content="response"))
```

#### 2. Environment Variable Issues
```
Error: DATABASE_URL not set
```
**Solution**: Use test environment setup:
```python
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
```

#### 3. Async Test Issues
```
Error: RuntimeError: There is no current event loop
```
**Solution**: Ensure proper async test configuration:
```python
@pytest.mark.asyncio
async def test_async_function():
    # Test code here
```

#### 4. Coverage Gaps
```
Warning: Coverage below threshold
```
**Solution**: Identify uncovered code and add targeted tests:
```bash
coverage report --show-missing
coverage html  # View detailed HTML report
```

### Performance Test Issues

#### 1. Inconsistent Response Times
**Causes**: System load, network latency, mock configuration
**Solutions**:
- Use controlled mocks with fixed delays
- Run tests in isolated environment
- Account for system performance variations

#### 2. Memory Leaks in Tests
**Symptoms**: Gradually increasing memory usage
**Solutions**:
- Add explicit cleanup in teardown
- Use garbage collection between tests
- Monitor memory usage patterns

### Integration Test Issues

#### 1. Database Connection Errors
**Solution**: Ensure test database is available:
```bash
# Start test database
docker run -d --name test-postgres -e POSTGRES_PASSWORD=testpass -p 5432:5432 postgres:15
```

#### 2. Authentication Issues
**Solution**: Use proper test authentication setup:
```python
@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
```

### Debugging Test Failures

#### 1. Verbose Output
```bash
pytest -v -s tests/unit/test_langgraph_graph.py::test_specific_function
```

#### 2. Debug Mode
```bash
pytest --pdb tests/unit/test_langgraph_graph.py::test_specific_function
```

#### 3. Log Output
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### Test Design

1. **Isolation**: Each test should be independent
2. **Deterministic**: Tests should produce consistent results
3. **Fast**: Unit tests should complete quickly
4. **Clear**: Test names should describe what is being tested
5. **Comprehensive**: Cover happy path, edge cases, and error conditions

### Mock Strategy

1. **Mock External Dependencies**: LLM, database, external APIs
2. **Use Realistic Data**: Mock responses should match real data
3. **Control Timing**: Use predictable delays for performance tests
4. **Test Error Cases**: Mock failures to test error handling

### Performance Testing

1. **Establish Baselines**: Set clear performance targets
2. **Measure Consistently**: Use controlled test environment
3. **Monitor Trends**: Track performance over time
4. **Test Under Load**: Validate behavior under stress

### Maintenance

1. **Regular Updates**: Keep tests current with code changes
2. **Review Coverage**: Monitor and improve coverage regularly
3. **Performance Monitoring**: Track performance trends
4. **Documentation**: Keep test documentation updated

---

This documentation provides comprehensive guidance for testing AI operations in the boardroom application. For additional support or questions, refer to the project's development team or create an issue in the project repository.
# CutePetsBoston Test Suite

This directory contains the test suite for CutePetsBoston.

## Structure

- `__init__.py` - Package initialization
- `conftest.py` - Shared pytest configuration and fixtures
- `fixtures/sample_data.json` - Sample RescueGroups API data for tests
- `test_pets.py` - Core tests for AdoptablePet, Post, and mock sources/sinks
- `test_data_utils.py` - Utilities and tests for sample data parsing
- `test_integration.py` - Integration tests combining multiple components
- `test_main.py` - Tests for main entrypoint and create_posters
- `test_source_manual.py` - Tests for manual adoption source

## Running Tests

### With pytest (recommended)

If you have pytest installed:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pets.py -v

# Run with coverage
pytest tests/ --cov=abstractions --cov=main --cov-report=html
```

## Test Categories

### Core Module Tests (`test_pets.py`)
- Tests for `AdoptablePet` and `Post` (from `abstractions`)
- Mock implementations of `PetSource` and a test-only `MockSocialSink`
- Integration-style tests with mock objects

### Data Utilities (`test_data_utils.py`)
- Load and parse sample data from `fixtures/sample_data.json`
- `RescueGroupsDataHelper` for working with API-shaped data
- Conversion from RescueGroups format to `AdoptablePet`
- Data filtering and querying tests

### Integration Tests (`test_integration.py`)
- End-to-end workflows using real sample data
- Error handling and edge cases
- Scalability testing
- Real data validation

## Sample Data

The test suite uses sample data from `tests/fixtures/sample_data.json`, containing RescueGroups-style API data:

- 3 sample pets (Doli, Kathy, Cylana)
- Complete API response structure
- Various pet attributes (size, age, breed, etc.)

## Mock Objects

The test suite provides mock implementations that can be used for testing:

```python
from tests.test_pets import MockPetSource, MockSocialSink
from abstractions import AdoptablePet, Post

# Create mock pets (use required fields: name, species, breed, location)
pets = [
    AdoptablePet(name="Fluffy", species="dog", breed="unknown", location="Unknown"),
    AdoptablePet(name="Spot", species="dog", breed="unknown", location="Unknown"),
]
pet_source = MockPetSource(pets)

# Create mock social sink
social_sink = MockSocialSink()

# Test workflow
for pet in pet_source.fetch_pets():
    post = Post(text=f"Meet {pet.name}!")
    social_sink.post(post)

# Verify results
assert len(social_sink.posted_content) == 2
```

## Adding New Tests

When adding functionality to `abstractions` or main flow, follow these steps:

1. Add unit tests to `test_pets.py` or `test_main.py` as appropriate
2. Add data parsing tests to `test_data_utils.py` if working with API data
3. Add integration tests to `test_integration.py` for end-to-end workflows
4. Update mock objects if new protocols are introduced
5. Run the full test suite to ensure compatibility

## Test Coverage

The test suite covers:

- ✅ Data structures (AdoptablePet, Post)
- ✅ Protocol implementations (PetSource, SocialPoster; mock sink for tests)
- ✅ Data parsing and conversion
- ✅ Integration workflows
- ✅ Error handling
- ✅ Edge cases and scalability

## Dependencies

- `pytest` (optional but recommended)
- `pytest-cov` (for coverage reports)
- Standard library modules: `json`, `pathlib`, `typing`, `unittest.mock`


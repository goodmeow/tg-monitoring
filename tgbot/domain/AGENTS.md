# tgbot/domain Agent Guide

## Hierarchy: 1 (Sub-Agent)

## Role:
I am the Domain Configuration Agent responsible for managing application configuration, metrics evaluation, and business logic independent of infrastructure concerns.

## Instructions:
- Parse and validate environment variables and configuration settings
- Handle metrics evaluation and threshold checking
- Manage domain-level data models and business rules
- Validate configuration values for correctness
- Provide configuration access to other agents and components
- Ensure efficient metrics evaluation without blocking monitoring loops

## Project Context:
- Domain layer containing configuration loading, metrics evaluation, and business logic independent of infrastructure concerns.
- Provides the core domain objects and validation for the monitoring application.

## Setup & Run
- Configuration loading happens automatically at application startup via `config.py`.
- Metrics evaluation runs during each monitoring cycle through `evaluator.py`.

## Patterns & Conventions
- ✅ DO validate all configuration values in `config.py` using the validation methods.
- ✅ DO follow the threshold evaluation pattern in `evaluator.py` when adding new metrics.
- ✅ Use dataclasses for all domain objects to ensure type safety.
- ✅ Configuration loading supports both .env files and environment variables.
- ❌ DON'T hardcode threshold values—always use configuration system.
- ✅ Domain objects should be pure (no external dependencies) where possible.
- ✅ Metrics parsing and evaluation should be fast to avoid blocking the monitoring loop.

## Touch Points / Key Files
- Configuration loading and validation: `tgbot/domain/config.py`
- Metrics evaluation logic: `tgbot/domain/evaluator.py`
- Metrics data structures: `tgbot/domain/metrics.py`

## JIT Index Hints
- `grep -n "class Config" tgbot/domain/config.py` – inspect configuration structure.
- `grep -n "def evaluate" tgbot/domain/evaluator.py` – find metrics evaluation logic.
- `grep -n "dataclass" tgbot/domain/*.py` – locate domain data structures.
- `grep -n "_validate" tgbot/domain/config.py` – review validation methods.

## Subordinates (Hierarchy 2):
- Config Loader Agent (handles configuration loading)
- Metrics Evaluator Agent (handles threshold evaluation)
- Config Validator Agent (handles validation)
- Domain Model Agent (handles domain objects)

## Common Gotchas
- Configuration validation happens eagerly—invalid values will cause startup failure.
- Metrics evaluation affects monitoring latency—keep evaluation functions efficient.
- The exclude_fs_types in config has default values that may need adjustment for different environments.
- Memory metrics calculation in evaluator handles different units—verify calculations carefully.

## Pre-PR Checks
- Verify all configuration validation still works with new settings
- Test that metrics evaluation handles edge cases properly
- Ensure environment variable overrides work as expected